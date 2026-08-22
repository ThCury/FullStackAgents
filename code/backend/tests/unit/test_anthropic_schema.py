"""Normalização do JSON Schema para o structured output.

Bug real que isto trava: a API devolve HTTP 400 quando algum objeto do schema
não declara `additionalProperties: false`. O `extra="forbid"` do Pydantic cobre
só o modelo de topo — os modelos aninhados em `$defs` ficavam sem, e todo run
em modo `anthropic` morria na primeira chamada.

Nenhum destes testes toca a rede: exercitam só a transformação do schema.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from agents.schemas import (
    BriefingAnalystOutput,
    DeveloperOutput,
    ProductOwnerOutput,
    QaOutput,
)
from infrastructure.llm.anthropic_adapter import _strict_schema


def _objetos_sem_guarda(node: Any, caminho: str = "$") -> list[str]:
    """Todo caminho de objeto que não declara `additionalProperties: false`."""
    faltando: list[str] = []
    if isinstance(node, list):
        for i, item in enumerate(node):
            faltando += _objetos_sem_guarda(item, f"{caminho}[{i}]")
        return faltando
    if not isinstance(node, dict):
        return faltando

    if node.get("type") == "object" and node.get("additionalProperties") is not False:
        faltando.append(caminho)
    for key, value in node.items():
        faltando += _objetos_sem_guarda(value, f"{caminho}.{key}")
    return faltando


@pytest.mark.parametrize(
    "model",
    [BriefingAnalystOutput, ProductOwnerOutput, DeveloperOutput, QaOutput],
    ids=lambda m: m.__name__,
)
def test_schema_de_cada_agente_fica_valido_para_a_api(model: type[BaseModel]) -> None:
    """O schema real de cada agente, do jeito que vai para a API."""
    normalizado = _strict_schema(model.model_json_schema())

    assert not _objetos_sem_guarda(normalizado), (
        "objetos sem `additionalProperties: false` -> HTTP 400 na chamada"
    )


def test_pydantic_cru_reproduz_o_bug() -> None:
    """Garante que o teste acima está medindo algo.

    Se um dia o Pydantic passar a emitir `additionalProperties: false` em todo
    `$defs`, este teste falha — e aí `_strict_schema` pode ser removida em vez
    de ficar como código morto que ninguém entende.
    """
    cru = BriefingAnalystOutput.model_json_schema()

    assert _objetos_sem_guarda(cru), (
        "o schema cru já vem válido; `_strict_schema` pode ser desnecessária agora"
    )


def test_preserva_a_estrutura_do_schema() -> None:
    """Normalizar não pode perder nem alterar propriedade."""
    cru = ProductOwnerOutput.model_json_schema()
    normalizado = _strict_schema(cru)

    assert normalizado["properties"].keys() == cru["properties"].keys()
    assert normalizado.get("required") == cru.get("required")
    assert normalizado["$defs"].keys() == cru["$defs"].keys()


def test_nao_muta_a_entrada() -> None:
    """`model_json_schema()` é cacheado pelo Pydantic — mutar vazaria para
    outras chamadas."""
    cru = QaOutput.model_json_schema()
    antes = repr(cru)

    _strict_schema(cru)

    assert repr(cru) == antes


def test_desce_em_listas_e_unioes() -> None:
    schema = {
        "type": "object",
        "properties": {
            "itens": {"type": "array", "items": {"type": "object", "properties": {}}},
            "ou": {"anyOf": [{"type": "object", "properties": {}}, {"type": "null"}]},
        },
    }

    normalizado = _strict_schema(schema)

    assert normalizado["additionalProperties"] is False
    assert normalizado["properties"]["itens"]["items"]["additionalProperties"] is False
    assert normalizado["properties"]["ou"]["anyOf"][0]["additionalProperties"] is False
    # `null` não é objeto: não deve receber a guarda.
    assert "additionalProperties" not in normalizado["properties"]["ou"]["anyOf"][1]
