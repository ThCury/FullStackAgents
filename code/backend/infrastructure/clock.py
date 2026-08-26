from domain.models.audit_time import AuditTime, now_audit_time


class BrasiliaClock:
    """Centraliza a criação dos dois horários exigidos pela auditoria."""

    def now(self) -> AuditTime:
        return now_audit_time()
