from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query, Request, status
from fastapi.encoders import jsonable_encoder

from application.project_presentation import ProjectPresentation
from domain.models.create_project_command import CreateProjectCommand
from domain.models.create_project_message_command import CreateProjectMessageCommand

router = APIRouter()


def _service(request: Request):
    return request.app.state.container.project_service


@router.post("/projects", status_code=status.HTTP_202_ACCEPTED)
def create_project(
    command: CreateProjectCommand, background_tasks: BackgroundTasks, request: Request
) -> dict:
    project, run = _service(request).create(command)
    background_tasks.add_task(request.app.state.container.run_service.execute, run["_id"])
    return {
        "project_id": project["_id"],
        "run_id": run["_id"],
        "status": run["status"],
        "brasil_datetime": run["brasil_datetime"],
    }


@router.get("/projects")
def list_projects(request: Request) -> dict:
    projects = _service(request).list_projects()
    return jsonable_encoder(
        {
            "total": len(projects),
            "projects": [ProjectPresentation.list_item(item) for item in projects],
        }
    )


@router.get("/projects/{project_id}")
def get_project(project_id: str, request: Request) -> dict:
    try:
        return jsonable_encoder(_service(request).get_or_raise(project_id))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/projects/{project_id}/messages", status_code=status.HTTP_202_ACCEPTED)
def continue_project(
    command: CreateProjectMessageCommand,
    background_tasks: BackgroundTasks,
    request: Request,
    project_id: str = Path(min_length=1),
) -> dict:
    try:
        _, run = _service(request).continue_project(project_id, command)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    background_tasks.add_task(request.app.state.container.run_service.execute, run["_id"])
    return {
        "project_id": project_id,
        "run_id": run["_id"],
        "retry_of_run_id": run.get("retry_of_run_id"),
        "status": run["status"],
        "brasil_datetime": run["brasil_datetime"],
    }


@router.get("/projects/{project_id}/messages")
def list_messages(
    project_id: str,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    try:
        messages, total = _service(request).messages(project_id, offset, limit)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return jsonable_encoder({"project_id": project_id, "total": total, "messages": messages})


@router.get("/projects/{project_id}/runs")
def list_project_runs(project_id: str, request: Request) -> dict:
    try:
        runs = _service(request).runs(project_id)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return jsonable_encoder({"project_id": project_id, "total": len(runs), "runs": runs})
