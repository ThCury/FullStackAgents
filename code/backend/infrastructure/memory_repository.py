from __future__ import annotations

from copy import deepcopy

from domain.models.audit_time import now_audit_time
from domain.models.product_backlog import ProductBacklog
from domain.models.run_status import RunStatus


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    def create(self, document: dict) -> None:
        if document["_id"] in self._documents:
            raise ValueError(f"Run já existe: {document['_id']}")
        self._documents[document["_id"]] = deepcopy(document)

    def get(self, run_id: str) -> dict | None:
        document = self._documents.get(run_id)
        return deepcopy(document) if document else None

    def mark_running(self, run_id: str) -> None:
        self._documents[run_id]["status"] = RunStatus.RUNNING.value

    def reserve_sequence(self, run_id: str) -> int:
        document = self._documents[run_id]
        document["audit"]["next_sequence"] += 1
        return document["audit"]["next_sequence"]

    def append_timeline(self, run_id: str, item: dict) -> None:
        self._documents[run_id]["audit"]["timeline"].append(deepcopy(item))

    def update_streaming_response(self, run_id: str, call_id: str, content: str) -> None:
        for item in self._documents[run_id]["audit"]["timeline"]:
            if item.get("call_id") == call_id:
                item["response"]["content"] = content
                return
        raise KeyError(f"Chamada não encontrada: {call_id}")

    def finish_call(self, run_id: str, call_id: str, fields: dict) -> None:
        for item in self._documents[run_id]["audit"]["timeline"]:
            if item.get("call_id") == call_id:
                for key, value in fields.items():
                    target = item
                    parts = key.split(".")
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = deepcopy(value)
                return
        raise KeyError(f"Chamada não encontrada: {call_id}")

    def finish_run(self, run_id: str, output: ProductBacklog, totals: dict) -> None:
        document = self._documents[run_id]
        document["output"] = output.model_dump()
        document["audit"]["totals"] = deepcopy(totals)
        document["status"] = RunStatus.COMPLETED.value
        document["finished_at"] = now_audit_time().model_dump()

    def fail_run(self, run_id: str, error: str) -> None:
        document = self._documents[run_id]
        document["status"] = RunStatus.FAILED.value
        document["error"] = error
        document["finished_at"] = now_audit_time().model_dump()
