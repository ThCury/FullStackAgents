from __future__ import annotations

import json
from pathlib import Path

from agents.agent_loop import AgentLoop, LoopOutcome
from agents.prompted_agent import PromptedAgent
from application.workspace_toolset import WorkspaceToolset
from domain.models.development_plan import DevelopmentPlan
from domain.models.llm_request import LLMRequest
from domain.models.product_backlog import ProductBacklog
from domain.ports.agent_auditor import AgentAuditor
from domain.ports.workspace_manager import WorkspaceManager


class DeveloperAgent(PromptedAgent):
    """Planeja a implementação explorando o workspace apenas em leitura."""

    role = "DEVELOPER"

    @classmethod
    def prompt_path(cls) -> Path:
        return Path(__file__).with_name("system_prompt.md")

    def build_request(self, backlog: ProductBacklog, template_manifest: str) -> LLMRequest:
        prompt = json.dumps(
            {"backlog": backlog.model_dump(), "template_manifest": template_manifest},
            ensure_ascii=False,
        )
        return LLMRequest(
            prompt=prompt,
            system_prompt=self.system_prompt,
            model=self._model,
            role=self.role,
            effort=self._effort,
        )

    def run(
        self,
        backlog: ProductBacklog,
        template_manifest: str,
        workspace_manager: WorkspaceManager,
        workspace: dict,
        auditor: AgentAuditor,
    ) -> tuple[DevelopmentPlan, LoopOutcome]:
        toolset = WorkspaceToolset(workspace_manager, workspace, writable=False)
        loop = AgentLoop(
            self._llm,
            auditor,
            toolset,
            self._max_iterations,
            self._max_retries,
            self._retry_base_delay_seconds,
        )
        outcome = loop.run(self.build_request(backlog, template_manifest))
        try:
            plan = DevelopmentPlan.model_validate(outcome.as_json())
        except ValueError as error:
            raise ValueError(f"Resposta do DEV não atende ao contrato: {error}") from error
        self._reject_unknown_paths(plan, workspace_manager.code_tree(workspace))
        return plan, outcome

    @staticmethod
    def _reject_unknown_paths(plan: DevelopmentPlan, tree: list[str]) -> None:
        """O plano só vale se falar de arquivos que existem — ou que ainda não existem."""
        existing = set(tree)
        declared = plan.files_to_change + plan.files_to_delete
        missing = [path for path in declared if path not in existing]
        if missing:
            raise ValueError(f"Plano cita arquivos ausentes do workspace: {sorted(missing)}")
        duplicated = [path for path in plan.files_to_create if path in existing]
        if duplicated:
            raise ValueError(f"Plano quer criar arquivos que já existem: {sorted(duplicated)}")
