from __future__ import annotations

from pathlib import Path

from agents.agent_loop import AgentLoop, LoopOutcome
from agents.prompted_agent import PromptedAgent
from domain.models.llm_request import LLMRequest
from domain.models.product_backlog import ProductBacklog
from domain.ports.agent_auditor import AgentAuditor


class ProductOwnerAgent(PromptedAgent):
    role = "PRODUCT_OWNER"

    @classmethod
    def prompt_path(cls) -> Path:
        return Path(__file__).with_name("system_prompt.md")

    def build_request(self, user_prompt: str) -> LLMRequest:
        return LLMRequest(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            model=self._model,
            role=self.role,
            effort=self._effort,
        )

    def run(self, user_prompt: str, auditor: AgentAuditor) -> tuple[ProductBacklog, LoopOutcome]:
        """O PO não recebe ferramentas: ele só interpreta o pedido do usuário."""
        loop = AgentLoop(self._llm, auditor, toolset=None, max_iterations=1)
        outcome = loop.run(self.build_request(user_prompt))
        try:
            backlog = ProductBacklog.model_validate(outcome.as_json())
        except ValueError as error:
            raise ValueError(f"Resposta do PO não atende ao contrato: {error}") from error
        return backlog, outcome
