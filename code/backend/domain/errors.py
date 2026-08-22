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


class LLMResponseTruncated(DomainError):
    """A resposta do modelo foi cortada por `max_tokens`.

    Falha **recuperável**: o run pode ser retomado depois de aumentar o teto,
    sem refazer o que já foi aprovado. Ver `POST /runs/{id}/retry`.
    """

    def __init__(self, agent: str, max_tokens: int, output_tokens: int) -> None:
        self.agent = agent
        self.max_tokens = max_tokens
        self.output_tokens = output_tokens
        super().__init__(
            f"[{agent}] resposta cortada em max_tokens={max_tokens} "
            f"(gerou {output_tokens}). Em claude-opus-5 o thinking consome o mesmo "
            f"teto da saída — aumente SQUAD_MAX_TOKENS_{agent.upper()} ou baixe o "
            f"effort deste papel. Aumentar o teto não encarece: cobra-se por token gerado."
        )


class LLMRefused(DomainError):
    """O classificador de segurança recusou a requisição."""

    def __init__(self, agent: str, category: str) -> None:
        self.agent = agent
        self.category = category
        super().__init__(f"[{agent}] requisição recusada pelo provider (categoria: {category})")


class LLMResponseInvalid(DomainError):
    """O modelo devolveu algo que não é JSON válido, sem ter sido truncado."""

    def __init__(self, agent: str, reason: str, excerpt: str = "") -> None:
        self.agent = agent
        self.reason = reason
        self.excerpt = excerpt
        super().__init__(f"[{agent}] resposta não é JSON válido: {reason} | final: ...{excerpt}")


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


class NoCheckpointAvailable(DomainError):
    """Nao existe estado salvo para retomar este run.

    Causa mais comum: `SQUAD_PERSISTENCE=memory`. O `MemorySaver` guarda o
    estado do grafo no processo, entao reiniciar o uvicorn apaga tudo. Para
    retomada entre reinicios, use `SQUAD_PERSISTENCE=mongo`.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(
            f"Run {run_id} nao tem checkpoint para retomar. "
            "Com SQUAD_PERSISTENCE=memory o estado morre com o processo — "
            "use SQUAD_PERSISTENCE=mongo para retomada durável."
        )


class RunNotRetryable(DomainError):
    """A retomada por checkpoint só faz sentido para um run que falhou."""

    def __init__(self, run_id: str, status: str) -> None:
        self.run_id = run_id
        self.status = status
        super().__init__(
            f"Run {run_id} está em '{status}' e não pode ser retomado por falha. "
            "Use /retry somente quando o status for 'failed'."
        )


class StoryNotFound(DomainError):
    def __init__(self, story_id: str) -> None:
        self.story_id = story_id
        super().__init__(f"Story {story_id} não encontrada")


class ScenarioCoverageMissing(DomainError):
    """`integrate` recusa fechar o run sem os 3 cenários da demo aceitos."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Cenários obrigatórios sem story aceita: {', '.join(missing)}")
