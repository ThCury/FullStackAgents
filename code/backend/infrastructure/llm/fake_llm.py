"""FakeLLM — implementação determinística de `LLMPort`.

É o que torna este repositório utilizável por um time no dia zero: `SQUAD_LLM=fake`
roda a esteira inteira, com auditoria e retrabalho, sem API key e sem custo.

Isso desacopla as frentes de trabalho. Quem está construindo o Console não fica
bloqueado por quem está afinando prompt; quem está no grafo não paga token para
testar um roteador.

Comportamento deliberado: a **primeira** avaliação do QA reprova. Não é bug — é
para que o ciclo Dev↔QA, o contador de retrabalho e a `MessageKind.REJECTION`
apareçam em todo run de desenvolvimento. O caminho felizão nunca exercita o
roteador condicional, que é justamente a parte interessante do grafo.
"""

from __future__ import annotations

import json
import re
from typing import Any

from domain.enums import AgentRole
from domain.ports.llm import LLMRequest, LLMResponse
from domain.value_objects import TokenUsage
from infrastructure.llm import fixtures

_MODEL_NAME = "fake-llm"


class FakeLLM:
    """`LLMPort` sem rede.

    `scripted` permite um teste forçar a resposta de um papel:
        FakeLLM(scripted={AgentRole.PRODUCT_OWNER: {...}})
    """

    def __init__(
        self,
        scripted: dict[AgentRole, dict[str, Any]] | None = None,
        reject_first_qa: bool = True,
    ) -> None:
        self._scripted = scripted or {}
        self._reject_first_qa = reject_first_qa
        self._qa_calls = 0
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        data = self._resolve(request)
        payload = json.dumps(data, ensure_ascii=False)
        return LLMResponse(
            data=data,
            raw_text=payload,
            model=_MODEL_NAME,
            usage=TokenUsage(
                input_tokens=len(request.system + request.user) // 4,
                output_tokens=len(payload) // 4,
            ),
            latency_ms=1,
        )

    async def count_tokens(self, request: LLMRequest) -> int:
        return len(request.system + request.user) // 4

    # ------------------------------------------------------------------ interno
    def _resolve(self, request: LLMRequest) -> dict[str, Any]:
        if scripted := self._scripted.get(request.agent):
            return scripted

        match request.agent:
            case AgentRole.BRIEFING_ANALYST:
                return fixtures.BRIEFING_ANALYST
            case AgentRole.PRODUCT_OWNER:
                return fixtures.PRODUCT_OWNER
            case AgentRole.DEVELOPER:
                title = _story_title(request.user)
                return fixtures.developer_output(
                    story_title=title,
                    slug=_slugify(title),
                    rework="<retrabalho" in request.user,
                )
            case AgentRole.QA:
                self._qa_calls += 1
                approve = not (self._reject_first_qa and self._qa_calls == 1)
                return fixtures.qa_output(
                    criteria_ids=_criterion_ids(request.user), approve=approve
                )
            case _:
                raise NotImplementedError(f"FakeLLM não cobre o papel {request.agent}")


def _block(text: str, tag: str) -> dict[str, Any] | None:
    """Extrai e desserializa um bloco `<tag>...</tag>` do prompt.

    Os agentes serializam os blocos de contexto com `as_json`, então dá para
    ler o objeto de verdade em vez de raspar com regex frágil.
    """
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _story_title(text: str) -> str:
    story = _block(text, "story") or {}
    return str(story.get("title") or "Entrega")


def _criterion_ids(text: str) -> list[str]:
    """Os ids de critério que o QA precisa cobrir (um caso por critério).

    Lê a lista real da story em vez de casar um padrão de id: o formato do id
    depende do `IdGeneratorPort` injetado (uuid em produção, sequencial em
    teste), e acoplar a fixture a ele já quebrou uma vez.
    """
    story = _block(text, "story") or {}
    ids = [
        str(c["id"])
        for c in story.get("acceptance_criteria", [])
        if isinstance(c, dict) and c.get("id")
    ]
    return ids or ["ac_desconhecido"]


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")
    return "_".join(slug.split("_")[:3]) or "entrega"
