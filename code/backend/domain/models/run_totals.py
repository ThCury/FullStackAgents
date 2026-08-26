from decimal import Decimal

from pydantic import BaseModel, Field

from domain.models.cost_value import CostValue


class RunTotals(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: CostValue = Field(default_factory=lambda: CostValue(amount=Decimal("0")))
    llm_latency_ms: int = 0

