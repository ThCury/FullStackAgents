from __future__ import annotations

from ...domain.entities.normalized_briefing import NormalizedBriefing
from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.agent import AgentContext
from ...domain.ports.workspace import ReadOnlyWorkspacePort
from ..base import BaseAgent
from ..tool_schemas import READ_ONLY_TOOLS
from ..utils import extract_json
from .prompt import SYSTEM_PROMPT


class BriefingAnalystAgent(BaseAgent):
    role = AgentRole.BRIEFING_ANALYST
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
        history = ctx.state.get("brief_history") or "(nenhuma execução anterior - este é o brief inicial)"
        return (
            f"Histórico de execuções anteriores do squad sobre esta aplicação:\n{history}\n\n"
            f"Briefing bruto do cliente para esta rodada:\n\n{ctx.state['raw_briefing']}\n\n"
            "Explore code/app se necessário e produza a NormalizedBriefing em JSON."
        )

    def parse_result(self, raw_text: str, ctx: AgentContext):
        data = extract_json(raw_text)
        briefing = NormalizedBriefing.from_dict(data)
        summary = (
            f"Briefing normalizado para {briefing.company or 'a aplicação'}: "
            f"{len(briefing.pains)} dores, {len(briefing.constraints)} restrições, "
            f"{len(briefing.open_questions)} perguntas abertas"
        )
        rationale = (
            "Estruturação sem interpretação (§5.1): normalizei o briefing em campos e glossário, "
            "sem escolher escopo, prioridade ou solução - isso é responsabilidade do PO."
        )
        return {"briefing": briefing.to_dict()}, MessageKind.HANDOFF, None, summary, rationale

    def next_agent(self, kind: MessageKind, state_updates: dict) -> AgentRole:
        return AgentRole.PRODUCT_OWNER
