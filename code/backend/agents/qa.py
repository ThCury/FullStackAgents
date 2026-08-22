"""QA Agent — intercepta a entrega do Dev, executa os testes, libera ou reprova.

O ponto que define este agente (§5.2): ele **executa**, não opina.
`TestRunnerPort` roda a suíte no sandbox e devolve evidência material; o LLM
escreve os casos e interpreta o resultado, mas o veredito é ancorado em execução
real. Um QA que só lê código e diz "parece ok" não atende o enunciado.

Cobertura é obrigatória: todo critério de aceite do PO precisa de ao menos um
caso. É o elo AC -> caso -> evidência que o avaliador vai percorrer.
"""

from __future__ import annotations

from typing import ClassVar

from agents.base import AgentPrompt, BaseAgent, as_json
from agents.prompts import load_prompt
from agents.schemas import QaOutput
from domain.entities.backlog import Story
from domain.entities.quality import Evidence, TestCase, TestReport
from domain.enums import AgentRole, MessageKind, TestOutcome, Verdict
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext


class QaAgent(BaseAgent[QaOutput]):
    role: ClassVar[AgentRole] = AgentRole.QA
    output_model: ClassVar[type[QaOutput]] = QaOutput
    # Aprovado segue para o orquestrador escolher a próxima story; reprovado
    # volta para o Dev. O `to_agent` real é ajustado em `message_kind_for`.
    to_agent: ClassVar[AgentRole] = AgentRole.ORCHESTRATOR
    message_kind: ClassVar[MessageKind] = MessageKind.DECISION

    def build_prompt(self, ctx: AgentContext) -> AgentPrompt:
        story = ctx.inputs.get("story")
        artifact = ctx.inputs.get("artifact")
        if not story or not artifact:
            raise AgentContractViolation(self.role, "story e/ou artifact ausentes em `inputs`")

        blocks = [
            f"<story>\n{as_json(story)}\n</story>",
            f"<entrega_do_dev>\n{as_json(artifact)}\n</entrega_do_dev>",
        ]
        # Resultado da execução real, injetado pelo nó antes de chamar o agente.
        if execution := ctx.inputs.get("execution_result"):
            blocks.append(
                "<execucao_real>\n"
                f"{as_json(execution)}\n"
                "</execucao_real>\n"
                "Ancore o veredito nesta execução. Não aprove critério cujo teste não rodou."
            )
        return AgentPrompt(system=load_prompt("qa"), user="\n\n".join(blocks))

    def summarize(self, payload: QaOutput) -> str:
        passed = sum(1 for c in payload.cases if c.outcome is TestOutcome.PASSED)
        verb = "APROVADA" if payload.verdict is Verdict.APPROVED else "REPROVADA"
        return f"{verb} — {passed}/{len(payload.cases)} casos passaram"

    def explain(self, payload: QaOutput) -> str:
        if payload.verdict is Verdict.APPROVED:
            return payload.summary
        changes = "; ".join(payload.required_changes[:3])
        return f"{payload.rejection_reason or payload.summary} | Requer: {changes}"

    def validate(self, payload: QaOutput, ctx: AgentContext) -> None:
        story = ctx.inputs.get("story")
        criteria_ids = (
            {c["id"] for c in story.get("acceptance_criteria", [])}
            if isinstance(story, dict)
            else set()
        )

        covered = {c.criterion_ref for c in payload.cases}
        if uncovered := criteria_ids - covered:
            raise AgentContractViolation(
                self.role,
                f"critérios de aceite sem caso de teste: {', '.join(sorted(uncovered))} — "
                "a cadeia AC -> caso -> evidência não pode ter buraco",
            )

        # Não se aprova entrega com caso falhando. É literalmente o papel:
        # "só libera o que estiver validado".
        failed = [c for c in payload.cases if c.outcome is TestOutcome.FAILED]
        if payload.verdict is Verdict.APPROVED and failed:
            raise AgentContractViolation(
                self.role,
                f"veredito APPROVED com {len(failed)} caso(s) reprovado(s)",
            )
        if payload.verdict is Verdict.REJECTED and not payload.required_changes:
            raise AgentContractViolation(
                self.role,
                "reprovação sem `required_changes` — o Dev entraria em loop "
                "sem saber o que corrigir",
            )

    def reference(self, ctx: AgentContext, payload: QaOutput) -> str | None:
        story = ctx.inputs.get("story")
        return story.get("id") if isinstance(story, dict) else None

    def assemble(
        self,
        payload: dict[str, object],
        run_id: str,
        story: Story,
        artifact_id: str,
        attempt: int,
        evidence: list[Evidence] | None = None,
    ) -> TestReport:
        parsed = QaOutput.model_validate(payload)
        shared_evidence = evidence or []

        return TestReport(
            id=self._ids.new_id("qa"),
            run_id=run_id,
            story_ref=story.id,
            artifact_ref=artifact_id,
            attempt=attempt,
            verdict=parsed.verdict,
            cases=[
                TestCase(
                    id=self._ids.new_id("case"),
                    criterion_ref=c.criterion_ref,
                    title=c.title,
                    steps=c.steps,
                    expected=c.expected,
                    outcome=c.outcome,
                    actual=c.actual,
                    evidence=shared_evidence,
                    duration_ms=c.duration_ms,
                )
                for c in parsed.cases
            ],
            summary=parsed.summary,
            rejection_reason=parsed.rejection_reason,
            required_changes=parsed.required_changes,
            created_at=self._clock.now(),
        )
