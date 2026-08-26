from __future__ import annotations

from uuid import uuid4

from agents.coder.agent import CoderAgent
from agents.developer.agent import DeveloperAgent
from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from domain.models.actor import Actor
from domain.models.audit_time import now_audit_time
from domain.models.create_run_command import CreateRunCommand
from domain.models.run_status import RunStatus
from domain.ports.run_repository import RunRepository
from domain.ports.workspace_manager import WorkspaceManager
from pipeline.graph import FullstackGraph


class RunService:
    def __init__(
        self,
        repository: RunRepository,
        product_owner: ProductOwnerAgent,
        developer: DeveloperAgent,
        coder: CoderAgent,
        workspace_manager: WorkspaceManager,
        cost_calculator: CostCalculator,
        stream_persist_interval_ms: int,
    ) -> None:
        self._repository = repository
        self._cost_calculator = cost_calculator
        self._graph = FullstackGraph(
            repository=repository,
            product_owner=product_owner,
            developer=developer,
            coder=coder,
            workspace_manager=workspace_manager,
            cost_calculator=cost_calculator,
            stream_persist_interval_ms=stream_persist_interval_ms,
        )

    def create(self, command: CreateRunCommand) -> dict:
        run_id = f"run_{uuid4().hex}"
        created_at = now_audit_time()
        user = Actor(
            type="user",
            id=command.requested_by_id,
            display_name=command.requested_by_name,
        )
        document = {
            "_id": run_id,
            "flow": "fullstack_po_dev_v1",
            "status": RunStatus.PENDING.value,
            "requested_by": user.model_dump(),
            "input": {
                "content": command.prompt,
                "recipient": {"id": "po", "role": "PRODUCT_OWNER"},
                "project_name": command.project_name,
                **created_at.model_dump(),
            },
            "audit": {
                "next_sequence": 0,
                "timeline": [],
                "totals": self._cost_calculator.totals(0, 0, 0, 0).model_dump(),
            },
            "output": None,
            "artifacts": [],
            **created_at.model_dump(),
            "finished_at": None,
            "error": None,
            "version": 1,
        }
        self._repository.create(document)
        self._append_event(
            run_id,
            "USER_PROMPT",
            {
                "from": user.model_dump(),
                "to": {"type": "agent", "id": "po", "role": "PRODUCT_OWNER"},
                "content": command.prompt,
                "attempt": 1,
            },
        )
        self._append_event(
            run_id,
            "FLOW_EVENT",
            {
                "event": "RUN_CREATED",
                "from": user.model_dump(),
                "to": {"type": "orchestrator", "id": "fullstack_graph"},
                "state_before": None,
                "state_after": RunStatus.PENDING.value,
                "attempt": 1,
                "approved": None,
                "summary": (
                    "Prompt recebido e persistido antes da execução do fluxo "
                    "PO → DEV → CODER."
                ),
            },
        )
        return self.get_or_raise(run_id)

    def execute(self, run_id: str) -> None:
        self._repository.mark_running(run_id)
        self._append_event(
            run_id,
            "FLOW_EVENT",
            {
                "event": "FLOW_STARTED",
                "from": {"type": "orchestrator", "id": "fullstack_graph"},
                "to": {"type": "agent", "id": "po", "role": "PRODUCT_OWNER"},
                "state_before": RunStatus.PENDING.value,
                "state_after": RunStatus.RUNNING.value,
                "attempt": 1,
                "approved": None,
                "summary": "Execução do fluxo PO → DEV → CODER iniciada.",
            },
        )
        run = self.get_or_raise(run_id)
        try:
            self._graph.invoke({"run_id": run_id, "user_prompt": run["input"]["content"]})
        except Exception as error:  # the failure itself must become part of the audit trail
            self._append_event(
                run_id,
                "FLOW_EVENT",
                {
                    "event": "AGENT_RESULT_REJECTED",
                    "from": {"type": "agent", "id": "po", "role": "PRODUCT_OWNER"},
                    "to": {"type": "orchestrator", "id": "fullstack_graph"},
                    "state_before": RunStatus.RUNNING.value,
                    "state_after": RunStatus.FAILED.value,
                    "attempt": 1,
                    "approved": False,
                    "summary": str(error),
                },
            )
            self._repository.fail_run(run_id, str(error))

    def get_or_raise(self, run_id: str) -> dict:
        document = self._repository.get(run_id)
        if document is None:
            raise KeyError(f"Run não encontrado: {run_id}")
        return document

    def list_runs(self) -> list[dict]:
        return self._repository.list_runs()

    def _append_event(self, run_id: str, item_type: str, fields: dict) -> None:
        time = now_audit_time()
        self._repository.append_timeline(
            run_id,
            {
                "sequence": self._repository.reserve_sequence(run_id),
                "type": item_type,
                **fields,
                **time.model_dump(),
            },
        )
