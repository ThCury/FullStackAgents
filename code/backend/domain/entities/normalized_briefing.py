"""Saída do BriefingAnalyst - ver §5.1 da arquitetura.

Propositalmente NÃO tem campo de escopo, prioridade ou solução: o Analyst
estrutura o problema, nunca o traduz em solução. Isso é trabalho do PO.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizedBriefing:
    company: str
    pains: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)
    methodology_refs: list[str] = field(default_factory=list)
    existing_app_notes: str = ""  # o que o Analyst observou já existir em code/app

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "pains": self.pains,
            "constraints": self.constraints,
            "actors": self.actors,
            "glossary": self.glossary,
            "open_questions": self.open_questions,
            "methodology_refs": self.methodology_refs,
            "existing_app_notes": self.existing_app_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedBriefing":
        return cls(
            company=data.get("company", ""),
            pains=data.get("pains", []),
            constraints=data.get("constraints", []),
            actors=data.get("actors", []),
            glossary=data.get("glossary", {}),
            open_questions=data.get("open_questions", []),
            methodology_refs=data.get("methodology_refs", []),
            existing_app_notes=data.get("existing_app_notes", ""),
        )
