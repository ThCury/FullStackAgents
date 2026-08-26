from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from domain.models.actor import Actor
from domain.models.audit_time import AuditTime
from domain.models.product_backlog import ProductBacklog
from domain.models.run_status import RunStatus


class RunDocument(BaseModel):
    id: str = Field(alias="_id")
    flow: str = "product_owner_v1"
    status: RunStatus = RunStatus.PENDING
    requested_by: Actor
    input: dict[str, Any]
    audit: dict[str, Any]
    output: ProductBacklog | None = None
    timestamp: datetime
    brasil_datetime: str
    timezone: str = "America/Sao_Paulo"
    finished_at: AuditTime | None = None
    error: str | None = None
    version: int = 1

    model_config = {"populate_by_name": True}

