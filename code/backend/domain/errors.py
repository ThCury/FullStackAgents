"""Erros de domínio. Nunca uma exceção de infraestrutura (pymongo, anthropic,
docker) deve vazar até aqui - a infraestrutura deve capturar e traduzir para
um destes erros, ou para um novo erro de domínio."""
from __future__ import annotations


class DomainError(Exception):
    pass


class BudgetExceeded(DomainError):
    def __init__(self, scope: str, spent_usd: float, limit_usd: float):
        super().__init__(
            f"Orçamento excedido em escopo '{scope}': ${spent_usd:.4f} gastos de ${limit_usd:.4f} permitidos"
        )
        self.scope = scope
        self.spent_usd = spent_usd
        self.limit_usd = limit_usd


class ReworkLimitReached(DomainError):
    def __init__(self, story_id: str, attempts: int):
        super().__init__(f"Story {story_id} atingiu o limite de retrabalho ({attempts} tentativas)")
        self.story_id = story_id
        self.attempts = attempts


class RunNotFound(DomainError):
    def __init__(self, run_id: str):
        super().__init__(f"Run não encontrado: {run_id}")
        self.run_id = run_id
