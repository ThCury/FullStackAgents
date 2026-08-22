"""PO Agent: transforma o brief enriquecido em backlog de user stories
priorizadas, com critérios de aceite claros e verificáveis pelo QA.
"""
from __future__ import annotations

from ..config import PO_MODEL
from ..tools import file_tools
from ..tools.schemas import READ_ONLY_TOOLS
from .base_agent import BaseAgent
from .utils import extract_json

SYSTEM_PROMPT = """\
Você é o Product Owner de um squad autônomo de agentes de software. Você é o
único elo entre o problema do cliente e o time técnico - o Dev e o QA nunca
veem o briefing original, apenas o que você escrever.

Você recebe o brief técnico enriquecido pelo Analista. Sua tarefa é quebrá-lo
em user stories priorizadas, pequenas o suficiente para serem implementadas e
validadas de forma independente, cobrindo o escopo definido.

Cada story precisa ter critérios de aceite objetivos e testáveis: o QA vai
validar o software EXCLUSIVAMENTE contra esses critérios, então evite critérios
vagos ("deve ser fácil de usar") e prefira critérios verificáveis por teste
automatizado ou inspeção de código ("o formulário rejeita submissão sem o
campo lote preenchido e exibe mensagem de erro").

Você pode usar list_dir/read_file para checar se já existe um backlog anterior
em pipeline/artifacts/backlog.json e evitar duplicar stories já entregues.

Responda SOMENTE com um array JSON, sem texto antes ou depois, no formato:
[
  {
    "id": "US-01",
    "title": "título curto",
    "description": "Como <persona>, quero <ação>, para <benefício>",
    "priority": "alta" | "media" | "baixa",
    "acceptance_criteria": ["critério 1", "critério 2", "..."]
  }
]

Ordene o array pela ordem de implementação recomendada (prioridade mais alta
primeiro). Gere entre 1 e 6 stories - o suficiente para cobrir o escopo desta
rodada sem fragmentar demais.
"""


class POAgent(BaseAgent):
    name = "po"
    model = PO_MODEL
    system_prompt = SYSTEM_PROMPT

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return file_tools.read_file(tool_input.get("rel_path", ""))
        if tool_name == "list_dir":
            return file_tools.list_dir(tool_input.get("rel_path", "."))
        return f"[erro] ferramenta desconhecida: {tool_name}"

    def run(self, state: dict) -> dict:
        user = (
            f"Brief técnico enriquecido pelo Analista:\n\n{state['enriched_brief']}\n\n"
            "Gere o backlog de user stories em JSON conforme instruído."
        )
        raw, _transcript = self.call_with_tools(user, READ_ONLY_TOOLS, self._execute_tool)
        backlog = extract_json(raw)

        self.write_json_artifact("backlog.json", backlog)

        first_id = backlog[0]["id"] if backlog else None
        summary = f"Backlog gerado com {len(backlog)} stories. Primeira story: {first_id or 'nenhuma'}."

        return {
            "backlog": backlog,
            "story_index": 0,
            "current_story_id": first_id,
            "revision_count": 0,
            "status": "in_dev" if first_id else "no_stories",
            "communication_log": [self.message("dev", summary)],
        }
