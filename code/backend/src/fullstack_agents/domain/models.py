from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


BRASILIA = ZoneInfo("America/Sao_Paulo")


class RunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AuditTime(BaseModel):
    timestamp: datetime
    brasil_datetime: str
    timezone: str = "America/Sao_Paulo"


def now_audit_time() -> AuditTime:
    instant = datetime.now(timezone.utc)
    brasilia = instant.astimezone(BRASILIA)
    return AuditTime(timestamp=instant, brasil_datetime=brasilia.isoformat())


class Actor(BaseModel):
    type: str
    id: str
    role: str | None = None
    display_name: str | None = None


class Requirement(BaseModel):
    id: str
    description: str
    priority: str = "must"


class UserStory(BaseModel):
    id: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: list[str] = Field(min_length=1)
    priority: str = "must"


class ProductBacklog(BaseModel):
    summary: str
    requirements: list[Requirement] = Field(min_length=1)
    user_stories: list[UserStory] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class CostValue(BaseModel):
    amount: Decimal
    currency: str = "USD"
    price_version: str = "local-config-v1"


class RunTotals(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: CostValue = Field(default_factory=lambda: CostValue(amount=Decimal("0")))
    llm_latency_ms: int = 0


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


class CreateRunCommand(BaseModel):
    prompt: str = Field(min_length=1, max_length=100_000)
    requested_by_id: str = Field(default="local-user", min_length=1)
    requested_by_name: str | None = Field(default="Usuário local", max_length=200)


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str
    model: str
    effort: str | None = None
    temperature: float = 0.2


class LLMCompleted(BaseModel):
    provider_response_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    finish_reason: str | None = None


class LLMStreamEvent(BaseModel):
    type: str
    delta: str = ""
    completed: LLMCompleted | None = None


class POState(BaseModel):
    run_id: str
    user_prompt: str
    backlog: ProductBacklog | None = None
    raw_response: str = ""
