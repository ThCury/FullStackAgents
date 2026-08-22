from __future__ import annotations

import uuid

from ... import config
from ...domain.entities.adr import ADR
from ...domain.entities.artifact import Artifact
from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.agent import AgentContext
from ...domain.ports.test_runner import TestRunnerPort
from ...domain.ports.workspace import CodeWorkspacePort
from ..base import BaseAgent
from ..tool_schemas import DEV_TOOLS
from ..utils import extract_json, find_story, last_rejection_feedback
from .prompt import SYSTEM_PROMPT


class DeveloperAgent(BaseAgent):
    role = AgentRole.DEVELOPER
    system_prompt = SYSTEM_PROMPT
    max_tool_iterations = config.DEV_MAX_TOOL_ITERATIONS

    def __init__(
        self,
        llm,
        message_repo,
        workspace: CodeWorkspacePort,
        test_runner: TestRunnerPort,
        model: str,
        effort: str,
        max_output_tokens: int,
    ):
        super().__init__(llm, message_repo)
        self._workspace = workspace
        self._test_runner = test_runner
        self.model = model
        self.effort = effort
        self.max_output_tokens = max_output_tokens

    def tools(self) -> list[dict]:
        return DEV_TOOLS

    def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "read_file":
            return self._workspace.read_file(tool_input.get("rel_path", ""))
        if name == "list_dir":
            return self._workspace.list_dir(tool_input.get("rel_path", "."))
        if name == "write_file":
            return self._workspace.write_file(tool_input.get("rel_path", ""), tool_input.get("content", ""))
        if name == "run_backend_tests":
            result = self._test_runner.run_backend_tests(tool_input.get("rel_path", "backend"))
            return f"exit_code={result.exit_code}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        return f"[erro] ferramenta desconhecida: {name}"

    def build_prompt(self, ctx: AgentContext) -> str:
        story = find_story(ctx.state["backlog"], ctx.state["current_story_id"])
        if story is None:
            raise ValueError(f"Story não encontrada no backlog: {ctx.state['current_story_id']}")

        parts = [f"User story {story['id']}: {story['title']}", story["description"], "Critérios de aceite (Gherkin):"]
        for ac in story["acceptance_criteria"]:
            parts.append(f"- Dado {ac['given']}\n  Quando {ac['when']}\n  Então {ac['then']}")

        feedback = last_rejection_feedback(ctx.state.get("test_reports", []), story["id"])
        if feedback:
            parts += [
                "",
                "RETRABALHO: o QA reprovou a entrega anterior desta story. Corrija especificamente isto:",
                feedback,
            ]

        parts.append("\nImplemente a story em code/app e responda com o JSON de decisão.")
        return "\n".join(parts)

    def parse_result(self, raw_text: str, ctx: AgentContext):
        data = extract_json(raw_text)
        story_id = ctx.state["current_story_id"]

        commit_sha = self._workspace.commit(f"feat({story_id}): {data['summary']}") or None

        artifact = Artifact(
            id=str(uuid.uuid4()),
            run_id=ctx.run_id,
            story_id=story_id,
            summary=data["summary"],
            files_changed=data.get("files_changed", []),
            tests_written=data.get("tests_written", []),
            commit_sha=commit_sha,
        )
        adr_data = data.get("adr", {})
        adr = ADR(
            id=str(uuid.uuid4()),
            run_id=ctx.run_id,
            story_ref=story_id,
            decision=adr_data.get("decision", ""),
            context=adr_data.get("context", ""),
            alternatives_considered=adr_data.get("alternatives_considered", []),
            rationale=adr_data.get("rationale", ""),
            consequences=adr_data.get("consequences", ""),
        )

        summary = f"Story {story_id}: {artifact.summary}"
        rationale = adr.rationale or "(sem justificativa registrada pelo Dev)"
        return (
            {"artifact": artifact.to_dict(), "adr": adr.to_dict()},
            MessageKind.DELIVERY,
            story_id,
            summary,
            rationale,
        )

    def next_agent(self, kind: MessageKind, state_updates: dict) -> AgentRole:
        return AgentRole.QA
