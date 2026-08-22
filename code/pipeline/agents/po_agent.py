"""PO Agent: transforma o brief enriquecido em backlog de user stories
priorizadas, com critérios de aceite claros e verificáveis pelo QA.
"""
from __future__ import annotations

from ..config import PO_MODEL
from .. import simple_project
from ..tools import file_tools
from ..tools.schemas import READ_ONLY_TOOLS
from .base_agent import BaseAgent
from .utils import extract_json

SYSTEM_PROMPT = """\
Você é o Product Owner de um squad autônomo de agentes de software. Você é o
único elo entre o problema do cliente e o time técnico - o Dev e o QA nunca
veem o briefing original, apenas o que você escrever.

Você recebe o brief técnico enriquecido pelo Analista, que já indica se esta
rodada é a construção inicial da aplicação ou um incremento sobre algo já
entregue em rodadas anteriores (e, nesse caso, o que já existe). Sua tarefa é
quebrar o escopo desta rodada em user stories priorizadas, pequenas o
suficiente para serem implementadas e validadas de forma independente. Gere
stories apenas para o escopo desta rodada - não recrie stories de
funcionalidades que o brief indica já estarem entregues.

Cada story precisa ter critérios de aceite objetivos e testáveis: o QA vai
validar o software EXCLUSIVAMENTE contra esses critérios, então evite critérios
vagos ("deve ser fácil de usar") e prefira critérios verificáveis por teste
automatizado ou inspeção de código ("o formulário rejeita submissão sem o
campo lote preenchido e exibe mensagem de erro").

Você pode usar list_dir/read_file para inspecionar o código já existente em
code/app antes de escrever as stories, garantindo que os critérios de aceite
sejam coerentes com o que já está implementado.

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
primeiro). Para a versão simplificada inicial da Trilha B, gere exatamente 3
stories, uma para cada cenário obrigatório da demo: registro ágil, causa raiz
assistida e rastreabilidade de lote. Se o brief desta rodada disser que é um
incremento ou pedir "somente" uma parte específica, gere apenas as stories desse
incremento. Não crie stories separadas de cadastros mestres, administração,
autenticação, banco de dados, dashboards ou integrações, a menos que o brief peça
isso explicitamente. Os dados de apoio podem ser semeados pelo Dev para manter a
demo pequena.
"""


class POAgent(BaseAgent):
    name = "po"
    model = PO_MODEL
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def _story_matches(story: dict, *terms: str) -> bool:
        haystack = f"{story.get('title', '')} {story.get('description', '')}".lower()
        return any(term in haystack for term in terms)

    def _scope_backlog(self, backlog: list[dict], state: dict) -> list[dict]:
        raw_brief = state.get("raw_brief", "").lower()
        if "somente" in raw_brief and "causa" in raw_brief:
            selected = [story for story in backlog if self._story_matches(story, "causa", "5 porqu", "plano de ac")]
            if selected:
                return selected[:1]
            return [
                {
                    "id": "US-01",
                    "title": "Causa raiz assistida com plano de acao",
                    "description": (
                        "Como responsavel pela investigacao de qualidade, quero abrir uma nao conformidade "
                        "existente, ver sugestoes de causa baseadas no historico e gerar plano de acao corretiva."
                    ),
                    "priority": "alta",
                    "acceptance_criteria": [
                        "A tela de causa raiz abre a partir de um registro de nao conformidade existente.",
                        "A analise apresenta 5 porques, sugestoes simples baseadas em historico semeado e causa provavel.",
                        "O sistema gera plano de acao corretiva com acao, responsavel, prazo e status.",
                        "A implementacao mantem a arquitetura simples existente, sem banco e sem frameworks novos.",
                    ],
                }
            ]
        return backlog

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return file_tools.read_file(tool_input.get("rel_path", ""))
        if tool_name == "list_dir":
            return file_tools.list_dir(tool_input.get("rel_path", "."))
        return f"[erro] ferramenta desconhecida: {tool_name}"

    def run(self, state: dict) -> dict:
        if self.simple_mode:
            backlog = self._scope_backlog(simple_project.BACKLOG, state)
            self.write_json_artifact("backlog.json", backlog)
            first_id = backlog[0]["id"] if backlog else None
            summary = f"Backlog simples gerado com {len(backlog)} stories. Primeira story: {first_id or 'nenhuma'}."
            return {
                "backlog": backlog,
                "story_index": 0,
                "current_story_id": first_id,
                "revision_count": 0,
                "status": "in_dev" if first_id else "no_stories",
                "communication_log": [self.message("dev", summary)],
            }

        user = (
            f"Brief técnico enriquecido pelo Analista:\n\n{state['enriched_brief']}\n\n"
            "Gere o backlog de user stories em JSON conforme instruído."
        )
        raw, _transcript = self.call_with_tools(user, READ_ONLY_TOOLS, self._execute_tool)
        try:
            backlog = extract_json(raw)
        except ValueError:
            if "somente" not in state.get("raw_brief", "").lower():
                raise
            backlog = []
        backlog = self._scope_backlog(backlog, state)

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
