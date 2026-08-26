from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from config import AgentLLMProfile, model_for_agent
from domain.models.llm_request import LLMRequest
from domain.models.product_backlog import ProductBacklog
from domain.ports.streaming_llm import StreamingLLM


class ProductOwnerAgent:
    role = "PRODUCT_OWNER"
    version = "1.0.0"

    @classmethod
    def llm_profile(cls) -> AgentLLMProfile:
        """O próprio agente declara qual perfil versionado utiliza."""
        return model_for_agent(cls.role)

    def __init__(self, llm: StreamingLLM, model: str, effort: str | None) -> None:
        self._llm = llm
        self._model = model
        self._effort = effort
        self.system_prompt = (
            Path(__file__).with_name("system_prompt.md").read_text(encoding="utf-8")
        )

    @property
    def provider(self) -> str:
        return self._llm.provider

    def build_request(self, user_prompt: str) -> LLMRequest:
        return LLMRequest(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            model=self._model,
            effort=self._effort,
        )

    def run(
        self, user_prompt: str, on_delta: Callable[[str], None]
    ) -> tuple[ProductBacklog, str, dict]:
        request = self.build_request(user_prompt)
        parts: list[str] = []
        completion: dict = {}
        for event in self._llm.stream(request):
            if event.type == "delta" and event.delta:
                parts.append(event.delta)
                on_delta(event.delta)
            elif event.type == "completed" and event.completed:
                completion = event.completed.model_dump()

        raw_response = "".join(parts)
        try:
            backlog = ProductBacklog.model_validate(json.loads(raw_response))
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"Resposta do PO não possui JSON válido: {error}") from error
        return backlog, raw_response, completion
