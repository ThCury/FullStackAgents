from __future__ import annotations

import json
from pathlib import Path

from agents.agent_loop import AgentLoop, LoopOutcome
from agents.prompted_agent import PromptedAgent
from application.workspace_toolset import WorkspaceToolset
from domain.models.development_plan import DevelopmentPlan
from domain.models.implementation_report import ImplementationReport
from domain.models.llm_request import LLMRequest
from domain.models.product_backlog import ProductBacklog
from domain.ports.agent_auditor import AgentAuditor
from domain.ports.workspace_manager import WorkspaceManager


class CoderAgent(PromptedAgent):
    """Executa o plano escrevendo no workspace através das ferramentas."""

    role = "CODER"

    @classmethod
    def prompt_path(cls) -> Path:
        return Path(__file__).with_name("system_prompt.md")

    def build_request(
        self,
        backlog: ProductBacklog,
        plan: DevelopmentPlan,
        template_manifest: str,
    ) -> LLMRequest:
        prompt = json.dumps(
            {
                "backlog": backlog.model_dump(),
                "development_plan": plan.model_dump(),
                "template_manifest": template_manifest,
            },
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
        plan: DevelopmentPlan,
        template_manifest: str,
        workspace_manager: WorkspaceManager,
        workspace: dict,
        auditor: AgentAuditor,
    ) -> tuple[ImplementationReport, list[dict[str, str]], LoopOutcome]:
        toolset = WorkspaceToolset(workspace_manager, workspace, writable=True)
        loop = AgentLoop(
            self._llm,
            auditor,
            toolset,
            self._max_iterations,
            self._max_retries,
            self._retry_base_delay_seconds,
        )
        outcome = loop.run(self.build_request(backlog, plan, template_manifest))
        try:
            report = ImplementationReport.model_validate(outcome.as_json())
        except ValueError as error:
            raise ValueError(f"Relatório do CODER não atende ao contrato: {error}") from error
        return report, toolset.writes, outcome
