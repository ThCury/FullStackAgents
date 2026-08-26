from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder

from application.run_presentation import RunPresentation
from domain.models.create_run_command import CreateRunCommand

router = APIRouter()


def _service(request: Request):
    return request.app.state.container.run_service


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def create_run(
    command: CreateRunCommand, background_tasks: BackgroundTasks, request: Request
) -> dict:
    service = _service(request)
    run = service.create(command)
    background_tasks.add_task(service.execute, run["_id"])
    return {
        "run_id": run["_id"],
        "status": run["status"],
        "brasil_datetime": run["brasil_datetime"],
    }


@router.get("/runs")
def list_runs(request: Request) -> dict:
    runs = _service(request).list_runs()
    return jsonable_encoder(
        {
            "total": len(runs),
            "runs": [RunPresentation.list_item(run) for run in runs],
        }
    )


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    request: Request,
    dataset: Literal["full", "resume"] = Query(default="resume"),
) -> dict:
    try:
        run = _service(request).get_or_raise(run_id)
        return jsonable_encoder(RunPresentation.render(run, dataset))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/runs/{run_id}/result")
def get_result(run_id: str, request: Request) -> dict:
    try:
        run = _service(request).get_or_raise(run_id)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if run["output"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Resultado ainda não está disponível."
        )
    return jsonable_encoder(run["output"])


@router.get("/runs/{run_id}/audit")
def get_audit(run_id: str, request: Request) -> dict:
    try:
        run = _service(request).get_or_raise(run_id)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return jsonable_encoder({"run_id": run_id, "status": run["status"], "audit": run["audit"]})
