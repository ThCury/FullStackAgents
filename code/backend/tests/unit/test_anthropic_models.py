"""Compatibilidade dos parâmetros com os modelos configuráveis da Anthropic.

Nenhum teste toca a rede: validamos o payload imediatamente antes de ele ser
enviado ao SDK.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from domain.enums import AgentRole, Effort
from domain.ports.llm import LLMRequest
from infrastructure.llm.anthropic_adapter import KNOWN_MODELS, AnthropicAdapter


def _request(max_tokens: int = 96_000) -> LLMRequest:
    return LLMRequest(
        run_id="run_modelo",
        agent=AgentRole.DEVELOPER,
        system="Responda seguindo o schema.",
        user="Implemente a story.",
        output_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        effort=Effort.XHIGH,
        max_tokens=max_tokens,
    )


def _params(model: str, max_tokens: int = 96_000) -> dict[str, Any]:
    client_sem_rede = cast(Any, object())
    adapter = AnthropicAdapter(client=client_sem_rede, model=model)
    return adapter._build_params(_request(max_tokens))


@pytest.mark.parametrize("model", ["claude-haiku-4-5", "claude-haiku-4-5-20251001"])
def test_haiku_45_limita_saida_e_omite_parametros_incompativeis(model: str) -> None:
    params = _params(model)

    assert params["max_tokens"] == 64_000
    assert "thinking" not in params
    assert "effort" not in params["output_config"]
    assert "format" in params["output_config"]


def test_limite_menor_que_64k_e_preservado() -> None:
    assert _params("claude-haiku-4-5", max_tokens=32_000)["max_tokens"] == 32_000


def test_modelo_com_teto_maior_preserva_perfil_do_dev() -> None:
    params = _params("claude-opus-5")

    assert params["max_tokens"] == 96_000
    assert params["thinking"] == {"type": "adaptive"}
    assert params["output_config"]["effort"] == "xhigh"


def test_id_oficial_fixo_do_haiku_e_aceito() -> None:
    assert "claude-haiku-4-5-20251001" in KNOWN_MODELS
