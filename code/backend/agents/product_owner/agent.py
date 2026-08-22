from __future__ import annotations

import json

from ...domain.entities.story import Story
from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.agent import AgentContext
from ...domain.ports.workspace import ReadOnlyWorkspacePort
from ..base import BaseAgent
from ..tool_schemas import READ_ONLY_TOOLS
from ..utils import extract_json
from .prompt import SYSTEM_PROMPT


class ProductOwnerAgent(BaseAgent):
    role = AgentRole.PRODUCT_OWNER
    system_prompt = SYSTEM_PROMPT

    def __init__(
        self, llm, message_repo, workspace: ReadOnlyWorkspacePort, model: str, effort: str, max_output_tokens: int
    ):
        super().__init__(llm, message_repo)
        self._workspace = workspace
        self.model = model
        self.effort = effort
        self.max_output_tokens = max_output_tokens

    def tools(self) -> list[dict]:
        return READ_ONLY_TOOLS

    def execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "read_file":
            return self._workspace.read_file(tool_input.get("rel_path", ""))
        if name == "list_dir":
            return self._workspace.list_dir(tool_input.get("rel_path", "."))
        return f"[erro] ferramenta desconhecida: {name}"

    def build_prompt(self, ctx: AgentContext) -> str:
        briefing = ctx.state.get("briefing") or {}
        return (
            f"NormalizedBriefing produzida pelo BriefingAnalyst:\n\n"
            f"{json.dumps(briefing, ensure_ascii=False, indent=2)}\n\n"
            "Gere o backlog de user stories em JSON conforme instruído."
        )

    def parse_result(self, raw_text: str, ctx: AgentContext):
        raw_stories = extract_json(raw_text)
        if not isinstance(raw_stories, list) or not all(isinstance(s, dict) for s in raw_stories):
            # Sinal quase sempre de resposta truncada (max_tokens insuficiente) fazendo o
            # extrator de JSON confundir um objeto com a lista inteira - erro explícito aqui
            # é preferível a um TypeError obscuro tentando montar Story a partir de string.
            raise ValueError(
                f"PO retornou JSON no formato inesperado (esperado: array de stories). "
                f"Tipo recebido: {type(raw_stories).__name__}. Resposta bruta:\n{raw_text[:1000]}"
            )
        run_id = ctx.run_id
        stories = [Story.from_dict({**s, "run_id": run_id}) for s in raw_stories]
        backlog = [s.to_dict() for s in stories]

        summary = f"Backlog gerado com {len(backlog)} stories priorizadas (MoSCoW)"
        rationale = (
            "Traduzi as dores/restrições da NormalizedBriefing em stories com critérios de aceite em "
            "Gherkin, resolvendo as perguntas abertas do Analyst na priorização."
        )
        return {"backlog": backlog}, MessageKind.DELIVERY, None, summary, rationale

    def next_agent(self, kind: MessageKind, state_updates: dict) -> AgentRole:
        return AgentRole.PIPELINE  # o próximo nó é o dispatch determinístico, não o Dev diretamente
