from typing import Literal

from pydantic import BaseModel, Field, model_validator

from domain.models.requirement import Requirement
from domain.models.user_story import UserStory

MAX_USER_STORIES = 10

REJECTION_MESSAGE = (
    "Este projeto é complexo demais para uma única entrega. Divida o pedido em "
    "partes menores e envie uma por vez, ou encaminhe o projeto para Thiago Cury "
    "Freire, meu líder."
)


class ProductBacklog(BaseModel):
    status: Literal["ACCEPTED", "TOO_COMPLEX"] = "ACCEPTED"
    summary: str
    estimated_stories: int = Field(ge=0)
    rejection: str | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    user_stories: list[UserStory] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status == "ACCEPTED"

    @model_validator(mode="after")
    def _validate_status_contract(self) -> "ProductBacklog":
        if self.status == "TOO_COMPLEX":
            return self._validate_rejection()
        return self._validate_acceptance()

    def _validate_rejection(self) -> "ProductBacklog":
        if self.requirements or self.user_stories:
            raise ValueError("Backlog recusado não pode conter requisitos ou histórias.")
        # O texto é normativo: o usuário precisa receber sempre a mesma orientação.
        if _normalized(self.rejection) != _normalized(REJECTION_MESSAGE):
            raise ValueError("Backlog recusado deve usar a mensagem de recusa exata.")
        self.rejection = REJECTION_MESSAGE
        return self

    def _validate_acceptance(self) -> "ProductBacklog":
        if not self.requirements or not self.user_stories:
            raise ValueError("Backlog aceito precisa de ao menos um requisito e uma história.")
        if len(self.user_stories) > MAX_USER_STORIES:
            raise ValueError(
                f"Backlog aceito excede o limite de {MAX_USER_STORIES} histórias de usuário."
            )
        self.rejection = None
        self._validate_traceability()
        return self

    def _validate_traceability(self) -> None:
        requirement_ids = {requirement.id for requirement in self.requirements}
        referenced: set[str] = set()
        for story in self.user_stories:
            unknown = set(story.requirement_ids) - requirement_ids
            if unknown:
                raise ValueError(
                    f"História {story.id} referencia requisito inexistente: {sorted(unknown)}"
                )
            referenced.update(story.requirement_ids)
        orphans = requirement_ids - referenced
        if orphans:
            raise ValueError(f"Requisitos sem história correspondente: {sorted(orphans)}")


def _normalized(text: str | None) -> str:
    return " ".join((text or "").split())
