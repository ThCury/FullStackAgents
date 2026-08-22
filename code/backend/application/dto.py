from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StartRunInput:
    raw_briefing: str
    budget_usd: float | None = None


@dataclass
class ApproveBudgetInput:
    run_id: str
    extra_budget_usd: float
