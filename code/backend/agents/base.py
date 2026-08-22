"""BaseAgent — o template method que torna a auditoria estrutural.

Por que isso não é opcional
---------------------------
O enunciado da Trilha B diz: "Um output final sem orquestração visível não será
considerado." Se cada agente fosse responsável por lembrar de emitir sua
`AgentMessage`, um esquecimento em code review custaria a nota.

Então a emissão vive aqui, no `run()` final. Uma subclasse não consegue
entregar sem registrar o handoff — ela sequer tem como: `run()` não é
sobrescrevível pelo contrato desta classe, e os hooks (`build_prompt`,
`summarize`, `validate`) não têm acesso ao repositório.

Ordem do template (não altere sem ADR):
    1. build_prompt   — hook da subclasse
    2. LLM            — structured output contra `output_schema`
    3. parse+validate — schema pydantic, depois `validate()` da subclasse
    4. persist        — LlmCall (cru) e AgentMessage (negócio)
    5. publish        — evento SSE para o Console
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from domain.entities.messaging import AgentMessage, LlmCall
from domain.enums import AgentRole, MessageKind
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext, AgentResult
from domain.ports.llm import LLMPort, LLMRequest
from domain.ports.observability import EventBusPort, SquadEvent
from domain.ports.repositories import LlmCallRepository, MessageRepository
from domain.ports.system import ClockPort, IdGeneratorPort
from domain.value_objects import AgentBudgetProfile


class AgentPrompt(BaseModel):
    """O que a subclasse monta. `system` precisa ser estável entre chamadas do
    mesmo papel — é o prefixo cacheável (§8.4)."""

    system: str
    user: str


def as_json(value: Any) -> str:
    """Serializa um bloco de contexto para o prompt.

    Sempre JSON, nunca `str(dict)`: o repr de dict do Python usa aspas simples e
    `None`/`True`, o que é ambíguo para o modelo e imprevisível para qualquer
    coisa que leia o prompt depois (inclusive o Inspector do Console).
    """
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


@dataclass(frozen=True, slots=True)
class AgentDeps:
    """As dependências que todo agente recebe.

    Um bundle explícito em vez de `**kwargs`: o container monta uma vez e passa
    o mesmo objeto para os quatro agentes, sem perder tipagem no caminho (um
    `dict[str, object]` espalhado com `**` apaga todos os tipos e o mypy deixa
    de proteger justamente a fiação, que é onde erro de composição mora).
    """

    llm: LLMPort
    messages: MessageRepository
    llm_calls: LlmCallRepository
    events: EventBusPort
    ids: IdGeneratorPort
    clock: ClockPort


class BaseAgent[TOut: BaseModel](ABC):
    # --- contrato de classe: cada agente declara seu papel e sua saída -------
    role: ClassVar[AgentRole]
    output_model: ClassVar[type[BaseModel]]
    to_agent: ClassVar[AgentRole]
    message_kind: ClassVar[MessageKind] = MessageKind.DELIVERY

    def __init__(self, deps: AgentDeps, profile: AgentBudgetProfile | None = None) -> None:
        self._llm = deps.llm
        self._messages = deps.messages
        self._llm_calls = deps.llm_calls
        self._events = deps.events
        self._ids = deps.ids
        self._clock = deps.clock
        self._profile = profile or AgentBudgetProfile()

    # ------------------------------------------------------------------ hooks
    @abstractmethod
    def build_prompt(self, ctx: AgentContext) -> AgentPrompt:
        """Monta system+user a partir do contexto."""

    @abstractmethod
    def summarize(self, payload: TOut) -> str:
        """Uma linha legível por humano para a timeline do Console."""

    def explain(self, payload: TOut) -> str:
        """O POR QUÊ do handoff. Sobrescreva quando o payload tiver a
        justificativa embutida (o PO tem `problem_interpretation`, o Dev tem
        ADRs, o QA tem `rejection_reason`)."""
        return ""

    def validate(self, payload: TOut, ctx: AgentContext) -> None:
        """Pós-condição do papel. Levante `AgentContractViolation`.

        É aqui que mora a regra "o PO precisa cobrir os 3 cenários" e "o QA
        precisa de um caso por critério de aceite". Schema garante forma;
        isto garante *suficiência*.
        """
        return None

    def reference(self, ctx: AgentContext, payload: TOut) -> str | None:
        """story_id / artifact_id que este handoff diz respeito."""
        return None

    # --------------------------------------------------------------- template
    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt = self.build_prompt(ctx)
        request = LLMRequest(
            run_id=ctx.run_id,
            agent=self.role,
            system=prompt.system,
            user=prompt.user,
            output_schema=self.output_model.model_json_schema(),
            effort=self._profile.effort,
            max_tokens=self._profile.max_tokens,
            cache_system=self._profile.cache_system_prompt,
        )

        # Orçamento NÃO é responsabilidade do agente: quem aplica é o decorator
        # `BudgetedLLM`, montado no container. Ver §8.3 e ADR de SRP.
        await self._publish(ctx.run_id, "node_started", {"agent": self.role})

        started = time.perf_counter()
        response = await self._llm.complete(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        call = LlmCall(
            id=response.call_id or self._ids.new_id("call"),
            run_id=ctx.run_id,
            agent=self.role,
            model=response.model,
            system_prompt=prompt.system,
            user_prompt=prompt.user,
            raw_response=response.raw_text,
            usage=response.usage,
            latency_ms=response.latency_ms or elapsed_ms,
            prompt_hash=_hash(prompt.system),
            effort=self._profile.effort,
            created_at=self._clock.now(),
        )
        await self._llm_calls.append(call)

        payload = self._parse(response.data)
        self.validate(payload, ctx)

        message = AgentMessage(
            id=self._ids.new_id("msg"),
            run_id=ctx.run_id,
            seq=await self._messages.next_seq(ctx.run_id),
            from_agent=self.role,
            to_agent=self.to_agent,
            kind=self.message_kind,
            ref=self.reference(ctx, payload),
            summary=self.summarize(payload),
            payload=payload.model_dump(mode="json"),
            rationale=self.explain(payload),
            usage=response.usage,
            llm_call_ref=call.id,
            created_at=self._clock.now(),
        )
        await self._messages.append(message)
        await self._publish(ctx.run_id, "message", message.model_dump(mode="json"))

        return AgentResult(
            role=self.role,
            payload=message.payload,
            message=message,
            usage=response.usage,
            kind=self.message_kind,
        )

    # --------------------------------------------------------------- internos
    def _parse(self, data: dict[str, Any]) -> TOut:
        try:
            return self.output_model.model_validate(data)  # type: ignore[return-value]
        except ValidationError as exc:
            raise AgentContractViolation(
                self.role, f"resposta fora do schema {self.output_model.__name__}: {exc}"
            ) from exc

    async def _publish(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        await self._events.publish(SquadEvent(run_id=run_id, type=event_type, payload=payload))


def _hash(text: str) -> str:
    """Hash do prefixo do prompt. Se muda a cada chamada, o cache nunca acerta."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]
