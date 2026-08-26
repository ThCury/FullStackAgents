from decimal import Decimal

from domain.models.cost_value import CostValue
from domain.models.run_totals import RunTotals


class CostCalculator:
    def __init__(
        self,
        input_price_per_million: Decimal = Decimal("0"),
        output_price_per_million: Decimal = Decimal("0"),
        price_version: str = "local-config-v1",
    ) -> None:
        self._input_price = input_price_per_million
        self._output_price = output_price_per_million
        self._price_version = price_version

    def totals(
        self,
        input_tokens: int | None,
        output_tokens: int | None,
        cached_tokens: int | None,
        latency_ms: int,
    ) -> RunTotals:
        input_value = input_tokens or 0
        output_value = output_tokens or 0
        cached_value = cached_tokens or 0
        estimated = (
            Decimal(input_value) / Decimal(1_000_000) * self._input_price
            + Decimal(output_value) / Decimal(1_000_000) * self._output_price
        )
        return RunTotals(
            input_tokens=input_value,
            output_tokens=output_value,
            cached_tokens=cached_value,
            total_tokens=input_value + output_value,
            estimated_cost=CostValue(amount=estimated, price_version=self._price_version),
            llm_latency_ms=latency_ms,
        )
