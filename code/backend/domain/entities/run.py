"""O Run — agregado raiz. Uma execução completa do squad."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import RunStatus, ScenarioTag
from domain.value_objects import BudgetPolicy, BudgetSnapshot


class Run(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    raw_briefing: str = Field(min_length=20)
    status: RunStatus = RunStatus.PENDING
    budget: BudgetSnapshot = Field(default_factory=BudgetSnapshot)
    workspace_path: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_reason: str | None = None
    awaiting_reason: str | None = Field(
        default=None, description="Preenchido quando o grafo pausa em `interrupt()`"
    )

    @classmethod
    def create(cls, run_id: str, briefing: str, policy: BudgetPolicy, now: datetime) -> Run:
        return cls(
            id=run_id,
            raw_briefing=briefing,
            status=RunStatus.PENDING,
            budget=BudgetSnapshot(policy=policy),
            created_at=now,
        )

    def with_status(self, status: RunStatus, **extra: object) -> Run:
        return self.model_copy(update={"status": status, **extra})

    @property
    def is_open(self) -> bool:
        return self.status in (RunStatus.PENDING, RunStatus.RUNNING, RunStatus.AWAITING_HUMAN)


class RunSummary(BaseModel):
    """Fecho do run, produzido pelo nó `integrate`.

    Materializa os 5 entregáveis do enunciado em um objeto só, para o Console
    e para export em disco.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    stories_total: int = 0
    stories_accepted: int = 0
    artifacts_delivered: int = 0
    adrs_recorded: int = 0
    test_cases_executed: int = 0
    test_cases_passed: int = 0
    rework_cycles: int = 0
    scenarios_covered: list[ScenarioTag] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    exported_files: list[str] = Field(default_factory=list)
    app_url: str | None = None
