from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceCriterion:
    """Critério de aceite em formato Gherkin - é o que permite ao QA gerar
    casos de teste automaticamente e ao avaliador conferir o rastro
    AC -> caso de teste -> evidência."""

    given: str
    when: str
    then: str

    def as_gherkin(self) -> str:
        return f"Dado {self.given}\nQuando {self.when}\nEntão {self.then}"

    def to_dict(self) -> dict:
        return {"given": self.given, "when": self.when, "then": self.then}

    @classmethod
    def from_dict(cls, data: dict) -> "AcceptanceCriterion":
        return cls(given=data["given"], when=data["when"], then=data["then"])
