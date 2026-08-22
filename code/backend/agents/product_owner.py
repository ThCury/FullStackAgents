"""PO Agent — o único autorizado a interpretar o problema do cliente.

Entregável: o backlog priorizado com critérios de aceite (Trilha B).
"""

from __future__ import annotations

from typing import ClassVar

from agents.base import AgentPrompt, BaseAgent, as_json
from agents.prompts import load_prompt
from agents.schemas import ProductOwnerOutput
from domain.entities.backlog import Backlog, Story
from domain.enums import AgentRole, MessageKind, ScenarioTag
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext
from domain.value_objects import AcceptanceCriterion


class ProductOwnerAgent(BaseAgent[ProductOwnerOutput]):
    role: ClassVar[AgentRole] = AgentRole.PRODUCT_OWNER
    output_model: ClassVar[type[ProductOwnerOutput]] = ProductOwnerOutput
    to_agent: ClassVar[AgentRole] = AgentRole.DEVELOPER
    message_kind: ClassVar[MessageKind] = MessageKind.DELIVERY

    def build_prompt(self, ctx: AgentContext) -> AgentPrompt:
        briefing = ctx.inputs.get("briefing")
        if not briefing:
            raise AgentContractViolation(self.role, "briefing normalizado ausente em `inputs`")
        return AgentPrompt(
            system=load_prompt("product_owner"),
            user=(
                "<briefing_normalizado>\n"
                f"{as_json(briefing)}\n"
                "</briefing_normalizado>\n\n"
                "Gere o backlog. Os 3 cenários obrigatórios da demo são: "
                f"{', '.join(t.value for t in ScenarioTag)}."
            ),
        )

    def summarize(self, payload: ProductOwnerOutput) -> str:
        covered = {s.scenario_tag for s in payload.stories if s.scenario_tag}
        return (
            f"Backlog com {len(payload.stories)} stories, "
            f"{len(covered)}/{len(ScenarioTag)} cenários cobertos"
        )

    def explain(self, payload: ProductOwnerOutput) -> str:
        out = payload.problem_interpretation
        if payload.out_of_scope:
            out += f" | Fora de escopo: {'; '.join(payload.out_of_scope[:3])}"
        return out

    def validate(self, payload: ProductOwnerOutput, ctx: AgentContext) -> None:
        """Os 3 cenários da demo são obrigatórios — o PDF os lista como
        "obrigatoriamente". Sem eles o run inteiro é inavaliável, e falhar aqui
        é muito mais barato que descobrir no `integrate`."""
        covered = {s.scenario_tag for s in payload.stories if s.scenario_tag is not None}
        missing = [t.value for t in ScenarioTag if t not in covered]
        if missing:
            raise AgentContractViolation(
                self.role, f"cenários obrigatórios sem story: {', '.join(missing)}"
            )

        for story in payload.stories:
            for idx, crit in enumerate(story.acceptance_criteria, start=1):
                if not all((crit.given.strip(), crit.when.strip(), crit.then.strip())):
                    raise AgentContractViolation(
                        self.role,
                        f"story '{story.title}' AC#{idx} incompleto — Gherkin exige "
                        "given/when/then preenchidos para o QA poder testar",
                    )

    def assemble(self, payload: dict[str, object], run_id: str) -> Backlog:
        """Promove drafts a `Story` com id estável, resolvendo `depends_on`."""
        parsed = ProductOwnerOutput.model_validate(payload)

        ids_by_title: dict[str, str] = {}
        for draft in parsed.stories:
            ids_by_title[draft.title] = self._ids.new_id("story")

        stories: list[Story] = []
        for draft in parsed.stories:
            story_id = ids_by_title[draft.title]
            criteria = [
                AcceptanceCriterion(id=f"{story_id}-ac{i}", given=c.given, when=c.when, then=c.then)
                for i, c in enumerate(draft.acceptance_criteria, start=1)
            ]
            stories.append(
                Story(
                    id=story_id,
                    title=draft.title,
                    narrative=draft.narrative,
                    priority=draft.priority,
                    scenario_tag=draft.scenario_tag,
                    acceptance_criteria=criteria,
                    depends_on=[
                        ids_by_title[t] for t in draft.depends_on_titles if t in ids_by_title
                    ],
                    rationale=draft.rationale,
                )
            )

        return Backlog(
            run_id=run_id,
            stories=stories,
            problem_interpretation=parsed.problem_interpretation,
            out_of_scope=parsed.out_of_scope,
            created_at=self._clock.now(),
        )
