"""BriefingAnalyst — o pré-PO.

Escopo restrito por decisão de arquitetura (§5.1 / ADR-07)
---------------------------------------------------------
O enunciado diz que o PO Agent "é o único ponto de contato com o problema do
cliente". Um Analyst que interpretasse o problema invadiria esse papel.

Então este agente faz **transformação sem interpretação**:
  ✅ estrutura, extrai glossário, levanta gaps, anexa metodologia
  ❌ requisito, story, prioridade, escopo, resposta aos próprios gaps

A `validate()` abaixo é o que impede a deriva de escopo virar bug silencioso.
"""

from __future__ import annotations

from typing import ClassVar

from agents.base import AgentPrompt, BaseAgent
from agents.prompts import load_prompt
from agents.schemas import BriefingAnalystOutput
from domain.entities.briefing import NormalizedBriefing
from domain.enums import AgentRole, MessageKind
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext

# Vocabulário que denuncia o Analyst interpretando em vez de normalizar.
_PRESCRIPTIVE_TERMS = (
    "user story",
    "como usuário",
    "critério de aceite",
    "sprint",
    "prioridade must",
    "devemos implementar",
    "a solução deve",
)


class BriefingAnalystAgent(BaseAgent[BriefingAnalystOutput]):
    role: ClassVar[AgentRole] = AgentRole.BRIEFING_ANALYST
    output_model: ClassVar[type[BriefingAnalystOutput]] = BriefingAnalystOutput
    to_agent: ClassVar[AgentRole] = AgentRole.PRODUCT_OWNER
    message_kind: ClassVar[MessageKind] = MessageKind.HANDOFF

    def build_prompt(self, ctx: AgentContext) -> AgentPrompt:
        raw = str(ctx.inputs.get("raw_briefing", "")).strip()
        if not raw:
            raise AgentContractViolation(self.role, "briefing cru ausente em `inputs`")
        return AgentPrompt(
            system=load_prompt("briefing_analyst"),
            user=f"<briefing_cru>\n{raw}\n</briefing_cru>",
        )

    def summarize(self, payload: BriefingAnalystOutput) -> str:
        return (
            f"Briefing normalizado: {len(payload.pains)} dores, "
            f"{len(payload.constraints)} restrições, "
            f"{len(payload.open_questions)} perguntas abertas"
        )

    def explain(self, payload: BriefingAnalystOutput) -> str:
        if not payload.open_questions:
            return "Briefing estruturado sem ambiguidades bloqueantes detectadas."
        gaps = "; ".join(q.question for q in payload.open_questions[:3])
        return f"Gaps levantados para o PO decidir (não respondidos aqui): {gaps}"

    def validate(self, payload: BriefingAnalystOutput, ctx: AgentContext) -> None:
        """Guarda de escopo: normalizar, não interpretar."""
        for pain in payload.pains:
            if not pain.verbatim.strip():
                raise AgentContractViolation(
                    self.role,
                    f"dor '{pain.statement[:40]}' sem `verbatim` — toda dor precisa "
                    "rastrear até o texto do cliente",
                )

        haystack = " ".join([payload.context, *(p.statement for p in payload.pains)]).casefold()
        for term in _PRESCRIPTIVE_TERMS:
            if term in haystack:
                raise AgentContractViolation(
                    self.role,
                    f"linguagem prescritiva detectada ('{term}'): o Analyst normaliza, "
                    "quem interpreta o problema é o PO Agent",
                )

    def assemble(self, payload: dict[str, object]) -> NormalizedBriefing:
        """Promove o draft a entidade de domínio."""
        return NormalizedBriefing.model_validate(payload)
