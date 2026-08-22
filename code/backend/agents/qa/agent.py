from __future__ import annotations

import uuid

from ... import config
from ...domain.entities.test_report import TestCase, TestReport
from ...domain.enums import AgentRole, MessageKind, Verdict
from ...domain.ports.agent import AgentContext
from ...domain.ports.test_runner import TestRunnerPort
from ...domain.ports.workspace import ReadOnlyWorkspacePort
from ..base import BaseAgent
from ..tool_schemas import QA_TOOLS
from ..utils import extract_json, find_story
from .prompt import SYSTEM_PROMPT


class QAAgent(BaseAgent):
    role = AgentRole.QA
    system_prompt = SYSTEM_PROMPT
    max_tool_iterations = config.QA_MAX_TOOL_ITERATIONS

    def __init__(
        self,
        llm,
        message_repo,
        workspace: ReadOnlyWorkspacePort,
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
        return QA_TOOLS

    def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "read_file":
            return self._workspace.read_file(tool_input.get("rel_path", ""))
        if name == "list_dir":
            return self._workspace.list_dir(tool_input.get("rel_path", "."))
        if name == "run_backend_tests":
            result = self._test_runner.run_backend_tests(tool_input.get("rel_path", "backend"))
            return f"exit_code={result.exit_code}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        if name == "run_frontend_tests":
            result = self._test_runner.run_frontend_tests(tool_input.get("rel_path", "frontend"))
            return f"exit_code={result.exit_code}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        return f"[erro] ferramenta desconhecida: {name}"

    def build_prompt(self, ctx: AgentContext) -> str:
        story = find_story(ctx.state["backlog"], ctx.state["current_story_id"])
        if story is None:
            raise ValueError(f"Story não encontrada no backlog: {ctx.state['current_story_id']}")
        artifact = ctx.state["artifacts"][-1]
        adr = ctx.state["adrs"][-1]

        ac_lines = [f"- Dado {ac['given']}\n  Quando {ac['when']}\n  Então {ac['then']}" for ac in story["acceptance_criteria"]]
        return (
            f"User story {story['id']}: {story['title']}\n{story['description']}\n\n"
            "Critérios de aceite (Gherkin):\n" + "\n".join(ac_lines) + "\n\n"
            "Entrega do Dev:\n"
            f"Resumo: {artifact['summary']}\n"
            f"Arquivos alterados: {', '.join(artifact['files_changed']) or '(nenhum informado)'}\n"
            f"Testes escritos: {', '.join(artifact['tests_written']) or '(nenhum informado)'}\n"
            f"ADR - decisão: {adr['decision']}\nADR - justificativa: {adr['rationale']}\n\n"
            "Faça o code review, execute os testes e responda com o JSON de veredito."
        )

    def parse_result(self, raw_text: str, ctx: AgentContext):
        data = extract_json(raw_text)
        story_id = ctx.state["current_story_id"]

        report = TestReport(
            id=str(uuid.uuid4()),
            run_id=ctx.run_id,
            story_ref=story_id,
            verdict=Verdict(data["verdict"]),
            test_cases=[TestCase(**c) for c in data.get("test_cases", [])],
            evidence=data.get("evidence", ""),
            feedback=data.get("feedback", ""),
        )

        approved = report.verdict == Verdict.APPROVED
        passed = sum(1 for c in report.test_cases if c.result == "pass")
        summary = f"Story {story_id}: {'APROVADA' if approved else 'REPROVADA'} ({passed}/{len(report.test_cases)} casos passaram)"

        kind = MessageKind.DELIVERY if approved else MessageKind.REJECTION
        return {"test_report": report.to_dict()}, kind, story_id, summary, report.feedback

    def next_agent(self, kind: MessageKind, state_updates: dict) -> AgentRole:
        return AgentRole.PIPELINE if kind == MessageKind.DELIVERY else AgentRole.DEVELOPER
