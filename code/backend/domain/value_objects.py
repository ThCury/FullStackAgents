"""Value objects — imutáveis, sem identidade, comparados por valor."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain.enums import Effort

# Preço de `claude-opus-5` (USD por 1M tokens) — ver ADR-05.
USD_PER_MTOK_INPUT = 5.00
USD_PER_MTOK_OUTPUT = 25.00


class Frozen(BaseModel):
    """Base de todo value object: imutável e sem campo extra silencioso."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenUsage(Frozen):
    """Consumo de uma chamada de LLM.

    `cache_read_tokens` existe porque é o único jeito honesto de saber se o
    prompt caching está funcionando — ver §8.4 da arquitetura.
    """

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        """Tokens lidos do cache custam ~10% do input — aproximação suficiente
        para o painel de custo; o número autoritativo é a fatura."""
        billed_input = self.input_tokens + self.cache_read_tokens * 0.1
        return (
            billed_input / 1_000_000 * USD_PER_MTOK_INPUT
            + self.output_tokens / 1_000_000 * USD_PER_MTOK_OUTPUT
        )

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )

    @classmethod
    def zero(cls) -> TokenUsage:
        return cls()


class BudgetPolicy(Frozen):
    """Teto de tokens em 3 escopos — ver §8.3 da arquitetura."""

    per_run: int = Field(default=2_000_000, gt=0)
    per_agent: int = Field(default=800_000, gt=0)
    per_call: int = Field(default=200_000, gt=0)

    @model_validator(mode="after")
    def _coherent(self) -> BudgetPolicy:
        if not self.per_call <= self.per_agent <= self.per_run:
            raise ValueError("orçamento incoerente: exige per_call <= per_agent <= per_run")
        return self


class BudgetSnapshot(Frozen):
    """Foto do consumo, carregada no estado do grafo para o Console ler."""

    policy: BudgetPolicy = Field(default_factory=BudgetPolicy)
    spent_by_agent: dict[str, int] = Field(default_factory=dict)
    total_spent: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    extensions_approved: int = Field(default=0, ge=0)

    @property
    def remaining(self) -> int:
        return max(0, self.policy.per_run - self.total_spent)


class AcceptanceCriterion(Frozen):
    """Critério de aceite em Gherkin.

    Não é preciosismo: é o que permite ao QA gerar o teste automaticamente e ao
    avaliador conferir o rastro AC -> caso de teste -> evidência (§5.2).
    """

    id: str
    given: str = Field(min_length=3)
    when: str = Field(min_length=3)
    then: str = Field(min_length=3)

    def to_gherkin(self) -> str:
        return f"Dado {self.given}\nQuando {self.when}\nEntão {self.then}"


class AgentBudgetProfile(Frozen):
    """Como cada papel gasta. Preenchido em `factory/settings.py`."""

    effort: Effort = Effort.HIGH
    max_tokens: int = Field(default=16_000, gt=0)
    cache_system_prompt: bool = True
