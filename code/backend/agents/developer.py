"""Dev Agent — consome a story, decide arquitetura, escreve código, registra ADR.

O enunciado pede "registra cada decisão técnica com justificativa". Por isso
`adrs` é obrigatório no schema e `alternatives_considered` tem `min_length=1`:
justificativa sem alternativa é racionalização, não decisão.
"""

from __future__ import annotations

from typing import ClassVar

from agents.base import AgentPrompt, BaseAgent, as_json
from agents.prompts import load_prompt
from agents.schemas import DeveloperOutput
from domain.entities.backlog import Story
from domain.entities.delivery import ADR, Artifact, SourceFile
from domain.enums import AgentRole, MessageKind
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext


class DeveloperAgent(BaseAgent[DeveloperOutput]):
    role: ClassVar[AgentRole] = AgentRole.DEVELOPER
    output_model: ClassVar[type[DeveloperOutput]] = DeveloperOutput
    to_agent: ClassVar[AgentRole] = AgentRole.QA
    message_kind: ClassVar[MessageKind] = MessageKind.DELIVERY

    def build_prompt(self, ctx: AgentContext) -> AgentPrompt:
        story = ctx.inputs.get("story")
        if not story:
            raise AgentContractViolation(self.role, "story ausente em `inputs`")

        blocks = [f"<story>\n{as_json(story)}\n</story>"]
        if scaffold := ctx.inputs.get("scaffold_contract"):
            blocks.append(f"<scaffold>\n{as_json(scaffold)}\n</scaffold>")

        # Retrabalho: o feedback do QA vira instrução explícita, não "tenta de novo".
        if ctx.feedback:
            changes = "\n".join(f"- {c}" for c in ctx.feedback)
            blocks.append(
                f'<retrabalho tentativa="{ctx.attempt}">\n'
                f"O QA reprovou a entrega anterior. Mudanças requeridas:\n{changes}\n"
                "Endereçe cada item e registre em ADR o que mudou de decisão.\n"
                "</retrabalho>"
            )

        return AgentPrompt(system=load_prompt("developer"), user="\n\n".join(blocks))

    def summarize(self, payload: DeveloperOutput) -> str:
        return (
            f"Entrega (tentativa) com {len(payload.files)} arquivo(s) e "
            f"{len(payload.adrs)} ADR(s): {', '.join(f.path for f in payload.files[:3])}"
        )

    def explain(self, payload: DeveloperOutput) -> str:
        return " | ".join(f"{a.title}: {a.rationale}" for a in payload.adrs[:3])

    def validate(self, payload: DeveloperOutput, ctx: AgentContext) -> None:
        for adr in payload.adrs:
            if not any(a.strip() for a in adr.alternatives_considered):
                raise AgentContractViolation(
                    self.role,
                    f"ADR '{adr.title}' sem alternativa real considerada — "
                    "justificativa sem alternativa é racionalização",
                )
        if not payload.how_to_verify.strip():
            raise AgentContractViolation(
                self.role,
                "`how_to_verify` vazio: o QA precisa saber como exercitar a entrega",
            )
        # Guarda de segurança: caminho é validado de novo na CodeWorkspacePort,
        # mas falhar aqui dá mensagem melhor no Console.
        for file in payload.files:
            if file.path.startswith("/") or ".." in file.path:
                raise AgentContractViolation(self.role, f"caminho fora do workspace: {file.path}")

    def reference(self, ctx: AgentContext, payload: DeveloperOutput) -> str | None:
        story = ctx.inputs.get("story")
        return story.get("id") if isinstance(story, dict) else None

    def assemble(
        self, payload: dict[str, object], run_id: str, story: Story, attempt: int
    ) -> Artifact:
        parsed = DeveloperOutput.model_validate(payload)
        artifact_id = self._ids.new_id("artifact")
        now = self._clock.now()

        return Artifact(
            id=artifact_id,
            run_id=run_id,
            story_ref=story.id,
            attempt=attempt,
            files=[SourceFile(path=f.path, content=f.content, kind=f.kind) for f in parsed.files],
            adrs=[
                ADR(
                    id=self._ids.new_id("adr"),
                    story_ref=story.id,
                    title=a.title,
                    context=a.context,
                    decision=a.decision,
                    alternatives_considered=a.alternatives_considered,
                    rationale=a.rationale,
                    consequences=a.consequences,
                    created_at=now,
                )
                for a in parsed.adrs
            ],
            implementation_notes=parsed.implementation_notes,
            how_to_verify=parsed.how_to_verify,
            created_at=now,
        )
