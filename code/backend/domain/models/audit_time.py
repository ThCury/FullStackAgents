from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

BRASILIA = ZoneInfo("America/Sao_Paulo")


class AuditTime(BaseModel):
    timestamp: datetime
    brasil_datetime: str
    timezone: str = "America/Sao_Paulo"


def now_audit_time() -> AuditTime:
    instant = datetime.now(UTC)
    brasilia = instant.astimezone(BRASILIA)
    return AuditTime(timestamp=instant, brasil_datetime=brasilia.isoformat())

