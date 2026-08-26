from decimal import Decimal

from pydantic import BaseModel


class CostValue(BaseModel):
    amount: Decimal
    currency: str = "USD"
    price_version: str = "local-config-v1"

