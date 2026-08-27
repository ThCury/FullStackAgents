from __future__ import annotations

import re
from pathlib import Path

from config import AgentLLMProfile, model_for_agent
from domain.ports.streaming_llm import StreamingLLM

VERSION_HEADER = re.compile(r"<!--\s*version:\s*([\w.\-]+)\s*-->")


class PromptedAgent:
    """Base dos agentes: carrega o system prompt e deriva a versão dele.

    A versão sai do próprio arquivo, não de uma constante no código, para que a
    auditoria nunca aponte para um prompt diferente do que foi enviado.
    """

    role: str = ""

    @classmethod
    def llm_profile(cls) -> AgentLLMProfile:
        return model_for_agent(cls.role)

    @classmethod
    def prompt_path(cls) -> Path:
        raise NotImplementedError

    def __init__(
        self,
        llm: StreamingLLM,
        model: str,
        effort: str | None,
        max_iterations: int = 24,
        max_retries: int = 3,
        retry_base_delay_seconds: float = 2.0,
    ) -> None:
        self._llm = llm
        self._model = model
        self._effort = effort
        self._max_iterations = max_iterations
        self._max_retries = max_retries
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self.system_prompt = self.prompt_path().read_text(encoding="utf-8")
        self.version = self._version_of(self.system_prompt)

    @property
    def provider(self) -> str:
        return self._llm.provider

    @staticmethod
    def _version_of(prompt: str) -> str:
        found = VERSION_HEADER.search(prompt)
        if not found:
            raise ValueError(
                "O system prompt precisa declarar a versão em um cabeçalho "
                "'<!-- version: ... -->' na primeira linha."
            )
        return found.group(1)
