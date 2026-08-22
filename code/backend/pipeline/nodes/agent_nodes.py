"""Nós que envolvem agentes de IA.

Um nó é um **adapter fino**: traduz `SquadState` -> `AgentContext`, chama o
agente, traduz `AgentResult` -> update de estado. Ele não decide nada.

Regra que mantém a arquitetura de pé: **regra de negócio não mora no nó.**
Se você está escrevendo um `if` sobre conteúdo de domínio aqui, ele pertence
ao agente (`validate()`), ao roteador (`pipeline/routers.py`) ou a um caso de
uso. O nó só transporta.
"""

from __future__ import annotations

from typing import Any

from agents.briefing_analyst import BriefingAnalystAgent
from agents.developer import DeveloperAgent
from agents.product_owner import ProductOwnerAgent
from agents.qa import QaAgent
from domain.entities.backlog import Story
from domain.enums import StoryStatus, Verdict
from domain.ports.agent import AgentContext
from domain.ports.execution import CodeWorkspacePort, TestRunnerPort
from domain.ports.repositories import (
    AdrRepository,
    ArtifactRepository,
    StoryRepository,
    TestReportRepository,
)
from pipeline.state import SquadState, current_story, latest_artifact


class IntakeNode:
    """BriefingAnalyst: normaliza o briefing cru."""

    def __init__(self, agent: BriefingAnalystAgent) -> None:
        self._agent = agent

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        result = await self._agent.run(
            AgentContext(
                run_id=state["run_id"],
                seq=0,
                inputs={"raw_briefing": state["raw_briefing"]},
            )
        )
        return {"briefing": result.payload}


class ProductOwnerNode:
    """PO: interpreta o problema e produz o backlog priorizado."""

    def __init__(self, agent: ProductOwnerAgent, stories: StoryRepository) -> None:
        self._agent = agent
        self._stories = stories

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        result = await self._agent.run(
            AgentContext(
                run_id=run_id,
                seq=0,
                inputs={"briefing": state.get("briefing")},
            )
        )

        backlog = self._agent.assemble(result.payload, run_id=run_id)
        ordered = backlog.ordered()
        await self._stories.save_many(run_id, ordered)

        return {
            "backlog": [s.model_dump(mode="json") for s in ordered],
            "queue": [s.id for s in ordered],
        }


class DeveloperNode:
    """Dev: decide arquitetura, escreve código no workspace, registra ADRs."""

    def __init__(
        self,
        agent: DeveloperAgent,
        artifacts: ArtifactRepository,
        adrs: AdrRepository,
        stories: StoryRepository,
        workspace: CodeWorkspacePort,
        scaffold_contract: str = "",
    ) -> None:
        self._agent = agent
        self._artifacts = artifacts
        self._adrs = adrs
        self._stories = stories
        self._workspace = workspace
        self._scaffold = scaffold_contract

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        story_dict = current_story(state)
        if story_dict is None:
            return {"failure": "DeveloperNode acionado sem story corrente"}

        story = Story.model_validate(story_dict)
        attempt = state.get("rework", {}).get(story.id, 0) + 1
        feedback = self._pending_feedback(state, story.id)

        result = await self._agent.run(
            AgentContext(
                run_id=run_id,
                seq=0,
                inputs={
                    "story": story_dict,
                    "scaffold_contract": self._scaffold,
                },
                feedback=feedback,
                attempt=attempt,
            )
        )

        artifact = self._agent.assemble(result.payload, run_id=run_id, story=story, attempt=attempt)

        # Grava em disco e versiona: é o que torna "escreve o código" verdadeiro.
        await self._workspace.write(run_id, artifact.files)
        await self._workspace.commit(run_id, f"[dev] {story.title} (tentativa {attempt})")

        await self._artifacts.append(artifact)
        await self._adrs.append_many(run_id, artifact.adrs)
        await self._stories.update(run_id, story.with_status(StoryStatus.IN_QA))

        return {
            "artifacts": [artifact.model_dump(mode="json")],
            "adrs": [a.model_dump(mode="json") for a in artifact.adrs],
        }

    def _pending_feedback(self, state: SquadState, story_id: str) -> list[str]:
        """As `required_changes` da última reprovação. É o que transforma
        "tenta de novo" em instrução acionável."""
        reports = [
            r
            for r in state.get("test_reports", [])
            if r.get("story_ref") == story_id and r.get("verdict") == Verdict.REJECTED.value
        ]
        return list(reports[-1].get("required_changes", [])) if reports else []


class QaNode:
    """QA: executa a suíte no sandbox, avalia contra os critérios, decide.

    A ordem importa: **executa primeiro, avalia depois**. O resultado da
    execução entra no prompt como fato. Se invertêssemos, o agente estaria
    opinando e depois procurando confirmação.
    """

    def __init__(
        self,
        agent: QaAgent,
        reports: TestReportRepository,
        stories: StoryRepository,
        runner: TestRunnerPort,
    ) -> None:
        self._agent = agent
        self._reports = reports
        self._stories = stories
        self._runner = runner

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        story_dict = current_story(state)
        if story_dict is None:
            return {"failure": "QaNode acionado sem story corrente"}

        story = Story.model_validate(story_dict)
        artifact = latest_artifact(state, story.id)
        if artifact is None:
            return {"failure": f"QaNode sem artefato para a story {story.id}"}

        test_paths = [f["path"] for f in artifact.get("files", []) if f.get("kind") == "test_code"]
        execution = await self._runner.run_api_tests(run_id, test_paths)

        result = await self._agent.run(
            AgentContext(
                run_id=run_id,
                seq=0,
                inputs={
                    "story": story_dict,
                    "artifact": artifact,
                    "execution_result": execution.model_dump(mode="json"),
                },
                attempt=artifact.get("attempt", 1),
            )
        )

        report = self._agent.assemble(
            result.payload,
            run_id=run_id,
            story=story,
            artifact_id=artifact["id"],
            attempt=artifact.get("attempt", 1),
            evidence=execution.evidence,
        )
        await self._reports.append(report)

        rework = dict(state.get("rework", {}))
        if report.verdict is Verdict.APPROVED:
            await self._stories.update(run_id, story.with_status(StoryStatus.ACCEPTED))
            queue = [sid for sid in state.get("queue", []) if sid != story.id]
        else:
            rework[story.id] = rework.get(story.id, 0) + 1
            await self._stories.update(run_id, story.with_status(StoryStatus.REWORK))
            queue = list(state.get("queue", []))

        return {
            "test_reports": [report.model_dump(mode="json")],
            "rework": rework,
            "queue": queue,
        }
