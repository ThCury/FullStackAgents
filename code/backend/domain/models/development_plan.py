from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ArchitectureDecision(BaseModel):
    decision: str
    rationale: str
    alternative_rejected: str


class ImplementationStep(BaseModel):
    id: str
    description: str
    story_ids: list[str] = Field(min_length=1)
    files: list[str] = Field(min_length=1)


class NewDependency(BaseModel):
    name: str
    target: Literal["frontend", "backend"]
    reason: str


class DevelopmentPlan(BaseModel):
    summary: str
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list)
    implementation_steps: list[ImplementationStep] = Field(min_length=1, max_length=25)
    files_to_create: list[str] = Field(default_factory=list)
    files_to_change: list[str] = Field(default_factory=list)
    files_to_delete: list[str] = Field(default_factory=list)
    new_dependencies: list[NewDependency] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _paths_are_disjoint(self) -> "DevelopmentPlan":
        buckets = {
            "files_to_create": set(self.files_to_create),
            "files_to_change": set(self.files_to_change),
            "files_to_delete": set(self.files_to_delete),
        }
        names = list(buckets)
        for index, name in enumerate(names):
            for other in names[index + 1 :]:
                shared = buckets[name] & buckets[other]
                if shared:
                    raise ValueError(
                        f"Caminho presente em {name} e {other}: {sorted(shared)}"
                    )
        return self

    def touched_paths(self) -> list[str]:
        return [*self.files_to_create, *self.files_to_change, *self.files_to_delete]
