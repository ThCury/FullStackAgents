from __future__ import annotations

from uuid import uuid4

from application.run_service import RunService
from domain.models.actor import Actor
from domain.models.audit_time import now_audit_time
from domain.models.create_project_command import CreateProjectCommand
from domain.models.create_project_message_command import CreateProjectMessageCommand
from domain.models.create_run_command import CreateRunCommand
from domain.models.project_status import ProjectStatus
from domain.models.run_mode import RunMode
from domain.ports.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository, run_service: RunService) -> None:
        self._repository = repository
        self._run_service = run_service

    def create(self, command: CreateProjectCommand) -> tuple[dict, dict]:
        project_id = f"project_{uuid4().hex}"
        time = now_audit_time()
        user = Actor(
            type="user",
            id=command.requested_by_id,
            display_name=command.requested_by_name,
        )
        project = {
            "_id": project_id,
            "name": command.name,
            "status": ProjectStatus.ACTIVE.value,
            "requested_by": user.model_dump(),
            "workspace": None,
            "context": {
                "summary": "Projeto criado; aguardando primeira execução.",
                "decisions": [],
                "backlog": None,
                "last_run_id": None,
            },
            "messages": [],
            "version": 1,
            **time.model_dump(),
        }
        self._repository.create(project)
        run = self._append_message_and_create_run(
            project,
            content=command.prompt,
            user=user,
            mode=RunMode.CREATE_PROJECT,
        )
        return self.get_or_raise(project_id), run

    def continue_project(
        self, project_id: str, command: CreateProjectMessageCommand
    ) -> tuple[dict, dict]:
        project = self.get_or_raise(project_id)
        if command.retry_run_id:
            run = self._run_service.retry_failed(command.retry_run_id, project_id)
            self._repository.set_last_run(project_id, run["_id"])
            return self.get_or_raise(project_id), run
        user = Actor(
            type="user",
            id=command.requested_by_id,
            display_name=command.requested_by_name,
        )
        mode = RunMode.CONTINUE_PROJECT if project.get("workspace") else RunMode.CREATE_PROJECT
        run = self._append_message_and_create_run(
            project,
            content=command.content or "",
            user=user,
            mode=mode,
        )
        return self.get_or_raise(project_id), run

    def create_legacy_run(self, command: CreateRunCommand) -> dict:
        """Mantém POST /runs: ele cria um projeto implícito."""
        _, run = self.create(
            CreateProjectCommand(
                name=command.project_name,
                prompt=command.prompt,
                requested_by_id=command.requested_by_id,
                requested_by_name=command.requested_by_name,
            )
        )
        return run

    def get_or_raise(self, project_id: str) -> dict:
        project = self._repository.get(project_id)
        if project is None:
            raise KeyError(f"Projeto não encontrado: {project_id}")
        return project

    def list_projects(self) -> list[dict]:
        return self._repository.list_projects()

    def messages(self, project_id: str, offset: int, limit: int) -> tuple[list[dict], int]:
        project = self.get_or_raise(project_id)
        messages = project["messages"]
        return messages[offset : offset + limit], len(messages)

    def runs(self, project_id: str) -> list[dict]:
        self.get_or_raise(project_id)
        return self._run_service.list_runs_for_project(project_id)

    def _append_message_and_create_run(
        self, project: dict, content: str, user: Actor, mode: RunMode
    ) -> dict:
        message_time = now_audit_time()
        message = {
            "id": f"msg_{uuid4().hex}",
            "role": "user",
            "author": user.model_dump(),
            "content": content,
            **message_time.model_dump(),
        }
        self._repository.append_message(project["_id"], message)
        run = self._run_service.create(
            CreateRunCommand(
                prompt=content,
                project_name=project["name"],
                requested_by_id=user.id,
                requested_by_name=user.display_name,
            ),
            project_id=project["_id"],
            trigger_message_id=message["id"],
            mode=mode,
        )
        self._repository.set_last_run(project["_id"], run["_id"])
        return run
