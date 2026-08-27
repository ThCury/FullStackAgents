from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from agents.coder.agent import CoderAgent
from agents.developer.agent import DeveloperAgent
from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from domain.models.audit_time import now_audit_time
from domain.models.development_plan import DevelopmentPlan
from domain.models.implementation_report import ImplementationReport
from domain.models.product_backlog import ProductBacklog
from domain.models.run_totals import RunTotals
from domain.ports.project_repository import ProjectRepository
from domain.ports.run_repository import RunRepository
from domain.ports.workspace_manager import WorkspaceManager
from pipeline.timeline_auditor import TimelineAuditor


class GraphState(TypedDict, total=False):
    run_id: str
    user_prompt: str
    backlog: ProductBacklog
    plan: DevelopmentPlan
    report: ImplementationReport
    workspace: dict[str, str]
    totals: list[RunTotals]
    project_id: str | None
    mode: str
    project_context: dict


class FullstackGraph:
    """Fluxo MVP: o PO especifica, o DEV planeja lendo o código e o CODER escreve."""

    def __init__(
        self,
        repository: RunRepository,
        product_owner: ProductOwnerAgent,
        developer: DeveloperAgent,
        coder: CoderAgent,
        project_repository: ProjectRepository | None,
        workspace_manager: WorkspaceManager,
        cost_calculator: CostCalculator,
        stream_persist_interval_ms: int,
    ) -> None:
        self._repository = repository
        self._product_owner = product_owner
        self._developer = developer
        self._coder = coder
        self._project_repository = project_repository
        self._workspace_manager = workspace_manager
        self._cost_calculator = cost_calculator
        self._stream_persist_interval_seconds = stream_persist_interval_ms / 1000

        builder = StateGraph(GraphState)
        builder.add_node("prepare", self._prepare)
        builder.add_node("specify", self._specify)
        builder.add_node("plan", self._plan)
        builder.add_node("implement", self._implement)
        builder.add_edge(START, "prepare")
        builder.add_conditional_edges(
            "prepare",
            self._after_prepare,
            {"specify": "specify", "plan": "plan"},
        )
        builder.add_conditional_edges(
            "specify",
            self._after_specify,
            {"plan": "plan", "end": END},
        )
        builder.add_edge("plan", "implement")
        builder.add_edge("implement", END)
        self._compiled = builder.compile()

    def invoke(self, state: GraphState) -> GraphState:
        return self._compiled.invoke(state)

    # --- nós ---------------------------------------------------------------

    @staticmethod
    def _prepare(state: GraphState) -> GraphState:
        return {}

    @staticmethod
    def _after_prepare(state: GraphState) -> str:
        return "plan" if state.get("backlog") else "specify"

    def _specify(self, state: GraphState) -> GraphState:
        run_id = state["run_id"]
        auditor = self._auditor_for(run_id, "po", self._product_owner)
        project_context = self._load_project_context(state.get("project_id"))
        backlog, _ = self._product_owner.run(
            self._prompt_with_project_context(state["user_prompt"], project_context), auditor
        )

        if not backlog.accepted:
            self._append_flow_event(
                run_id,
                "PO_BACKLOG_REJECTED",
                backlog.rejection or "Backlog recusado pelo Product Owner.",
                False,
                "po",
                "PRODUCT_OWNER",
            )
            self._repository.finish_run(run_id, backlog, auditor.totals.model_dump())
            self._update_project_context(state.get("project_id"), run_id, backlog)
            return {
                "backlog": backlog,
                "totals": [auditor.totals],
                "project_context": project_context,
            }

        self._append_flow_event(
            run_id,
            "PO_BACKLOG_ACCEPTED",
            "Backlog de produto criado pelo Product Owner.",
            True,
            "po",
            "PRODUCT_OWNER",
        )
        self._repository.set_backlog_snapshot(run_id, backlog.model_dump())
        return {
            "backlog": backlog,
            "totals": [auditor.totals],
            "project_context": project_context,
        }

    @staticmethod
    def _after_specify(state: GraphState) -> str:
        """Recusa do PO encerra a run com sucesso: não é erro, é escopo."""
        return "plan" if state["backlog"].accepted else "end"

    def _plan(self, state: GraphState) -> GraphState:
        run_id = state["run_id"]
        run = self._repository.get(run_id)
        if run is None:
            raise KeyError(f"Run não encontrado: {run_id}")

        workspace, created = self._workspace_for(state, run)
        self._append_artifact(run_id, "workspace", workspace)
        self._append_flow_event(
            run_id,
            "DEV_WORKSPACE_CREATED" if created else "DEV_WORKSPACE_REUSED",
            (
                "Workspace isolado criado a partir do template de referência."
                if created
                else "Workspace persistente do projeto reutilizado."
            ),
            True,
            "dev",
            "DEVELOPER",
        )

        auditor = self._auditor_for(run_id, "dev", self._developer)
        plan, outcome = self._developer.run(
            state["backlog"],
            self._workspace_manager.template_manifest(),
            self._workspace_manager,
            workspace,
            auditor,
        )
        plan_path = self._workspace_manager.write_artifact(
            workspace, f"{run_id}/development-plan.json", plan.model_dump_json(indent=2)
        )
        self._append_artifact(
            run_id,
            "development_plan",
            {
                "path": str(plan_path),
                "content": plan.model_dump(),
                "tool_iterations": outcome.iterations,
            },
        )
        self._append_flow_event(
            run_id,
            "DEV_PLAN_READY",
            f"Plano de implementação pronto após {outcome.iterations} iterações.",
            True,
            "dev",
            "DEVELOPER",
        )
        return {
            "plan": plan,
            "workspace": workspace,
            "totals": [*state["totals"], auditor.totals],
        }

    def _implement(self, state: GraphState) -> GraphState:
        run_id = state["run_id"]
        workspace = state["workspace"]
        auditor = self._auditor_for(run_id, "coder", self._coder)
        report, writes, outcome = self._coder.run(
            state["backlog"],
            state["plan"],
            self._workspace_manager.template_manifest(),
            self._workspace_manager,
            workspace,
            auditor,
        )
        report_path = self._workspace_manager.write_artifact(
            workspace, f"{run_id}/implementation-report.json", report.model_dump_json(indent=2)
        )
        divergences = report.divergence_from(writes)
        self._append_artifact(
            run_id,
            "implementation_report",
            {
                "path": str(report_path),
                "content": report.model_dump(),
                "performed_writes": writes,
                "divergences": divergences,
                "tool_iterations": outcome.iterations,
                "diff_stat": self._workspace_manager.diff(workspace),
            },
        )
        if divergences:
            self._append_flow_event(
                run_id,
                "CODER_REPORT_DIVERGED",
                "; ".join(divergences),
                False,
                "coder",
                "CODER",
            )
        self._append_flow_event(
            run_id,
            "CODER_IMPLEMENTATION_READY",
            f"{len(writes)} arquivo(s) gravado(s) em {outcome.iterations} iterações.",
            True,
            "coder",
            "CODER",
        )

        totals = [*state["totals"], auditor.totals]
        self._repository.finish_run(
            run_id,
            state["backlog"],
            self._cost_calculator.combine(*totals).model_dump(),
        )
        self._update_project_context(
            state.get("project_id"),
            run_id,
            state["backlog"],
            state["plan"],
            state["report"],
        )
        self._append_flow_event(
            run_id,
            "RUN_COMPLETED",
            "Fluxo PO → DEV → CODER concluído.",
            True,
            "coder",
            "CODER",
        )
        return {"report": report, "totals": totals}

    def _workspace_for(self, state: GraphState, run: dict) -> tuple[dict, bool]:
        project_id = state.get("project_id")
        if project_id and self._project_repository:
            project = self._project_repository.get(project_id)
            if project is None:
                raise KeyError(f"Projeto não encontrado: {project_id}")
            if project.get("workspace"):
                return self._workspace_manager.open_project_workspace(project["workspace"]), False
            workspace = self._workspace_manager.create_project(
                state["run_id"], run["input"].get("project_name", "novo-projeto")
            )
            self._project_repository.set_workspace(project_id, workspace)
            return workspace, True
        return (
            self._workspace_manager.create_project(
                state["run_id"], run["input"].get("project_name", "novo-projeto")
            ),
            True,
        )

    def _load_project_context(self, project_id: str | None) -> dict:
        if not project_id or not self._project_repository:
            return {}
        project = self._project_repository.get(project_id)
        if project is None:
            raise KeyError(f"Projeto não encontrado: {project_id}")
        return project.get("context", {})

    @staticmethod
    def _prompt_with_project_context(prompt: str, context: dict) -> str:
        if not context or not context.get("backlog"):
            return prompt
        return (
            "Contexto do projeto existente:\n"
            f"Resumo: {context.get('summary', '')}\n"
            f"Backlog vigente: {context['backlog']}\n\n"
            "Nova instrução do usuário:\n"
            f"{prompt}"
        )

    def _update_project_context(
        self,
        project_id: str | None,
        run_id: str,
        backlog: ProductBacklog,
        plan: DevelopmentPlan | None = None,
        report: ImplementationReport | None = None,
    ) -> None:
        if not project_id or not self._project_repository:
            return
        previous = self._project_repository.get(project_id)
        if previous is None:
            return
        self._project_repository.update_context(
            project_id,
            {
                "summary": report.summary if report else backlog.summary,
                "decisions": (
                    [decision.model_dump() for decision in plan.architecture_decisions]
                    if plan
                    else previous["context"]["decisions"]
                ),
                "backlog": backlog.model_dump(),
                "last_run_id": run_id,
            },
        )

    # --- auditoria ---------------------------------------------------------

    def _auditor_for(self, run_id: str, agent_id: str, agent: Any) -> TimelineAuditor:
        return TimelineAuditor(
            repository=self._repository,
            cost_calculator=self._cost_calculator,
            run_id=run_id,
            agent_id=agent_id,
            role=agent.role,
            version=agent.version,
            provider=agent.provider,
            stream_persist_interval_seconds=self._stream_persist_interval_seconds,
        )

    def _append_artifact(self, run_id: str, artifact_type: str, content: dict[str, Any]) -> None:
        time = now_audit_time()
        self._repository.append_artifact(
            run_id,
            {
                "id": f"artifact_{uuid4().hex}",
                "type": artifact_type,
                "content": content,
                **time.model_dump(),
            },
        )

    def _append_flow_event(
        self,
        run_id: str,
        event: str,
        summary: str,
        approved: bool | None,
        target_id: str,
        target_role: str,
    ) -> None:
        time = now_audit_time()
        self._repository.append_timeline(
            run_id,
            {
                "sequence": self._repository.reserve_sequence(run_id),
                "type": "FLOW_EVENT",
                "event": event,
                "from": {"type": "orchestrator", "id": "fullstack_graph"},
                "to": {"type": "agent", "id": target_id, "role": target_role},
                "attempt": 1,
                "approved": approved,
                "summary": summary,
                **time.model_dump(),
            },
        )
