from __future__ import annotations

from copy import deepcopy


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    def create(self, document: dict) -> None:
        if document["_id"] in self._documents:
            raise ValueError(f"Projeto já existe: {document['_id']}")
        self._documents[document["_id"]] = deepcopy(document)

    def get(self, project_id: str) -> dict | None:
        document = self._documents.get(project_id)
        return deepcopy(document) if document else None

    def list_projects(self) -> list[dict]:
        documents = sorted(
            self._documents.values(), key=lambda document: document["timestamp"], reverse=True
        )
        return deepcopy(documents)

    def append_message(self, project_id: str, message: dict) -> None:
        self._documents[project_id]["messages"].append(deepcopy(message))

    def set_workspace(self, project_id: str, workspace: dict) -> None:
        self._documents[project_id]["workspace"] = deepcopy(workspace)

    def update_context(self, project_id: str, context: dict) -> None:
        self._documents[project_id]["context"] = deepcopy(context)

    def set_last_run(self, project_id: str, run_id: str) -> None:
        self._documents[project_id]["context"]["last_run_id"] = run_id
