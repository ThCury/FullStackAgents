"""Erros de domínio.

Nenhum deles é `Exception` genérica: o roteador do grafo decide o caminho a
partir do *tipo* do erro. Ver `pipeline/routers.py`.
"""


class DomainError(Exception):
    """Raiz de todos os erros de domínio."""


class BudgetExceeded(DomainError):
    """Orçamento de tokens estourado.

    Não mata o run: o grafo roteia para `escalate` e pede aprovação humana.
    """

    def __init__(self, run_id: str, scope: str, spent: int, limit: int) -> None:
        self.run_id = run_id
        self.scope = scope
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"Orçamento estourado em '{scope}' do run {run_id}: {spent} > {limit} tokens"
        )


class ReworkLimitReached(DomainError):
    """QA reprovou a mesma story vezes demais. Escala para humano."""

    def __init__(self, story_id: str, attempts: int) -> None:
        self.story_id = story_id
        self.attempts = attempts
        super().__init__(f"Story {story_id} reprovada {attempts}x — escalando para humano")


class AgentContractViolation(DomainError):
    """O agente devolveu algo que não satisfaz o contrato do seu papel.

    Exemplos reais: PO sem cobrir os 3 cenários, QA sem caso de teste para um
    critério de aceite, Dev sem `alternatives_considered` na ADR.
    """

    def __init__(self, role: str, reason: str) -> None:
        self.role = role
        self.reason = reason
        super().__init__(f"[{role}] violou o contrato do papel: {reason}")


class RunNotFound(DomainError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run {run_id} não encontrado")


class StoryNotFound(DomainError):
    def __init__(self, story_id: str) -> None:
        self.story_id = story_id
        super().__init__(f"Story {story_id} não encontrada")


class ScenarioCoverageMissing(DomainError):
    """`integrate` recusa fechar o run sem os 3 cenários da demo aceitos."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Cenários obrigatórios sem story aceita: {', '.join(missing)}")
