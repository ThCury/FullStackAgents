"""QA Agent: intercepta cada entrega do Dev, faz code review contra os
critérios de aceite da story, roda testes de integração (e um e2e leve quando
aplicável) e só aprova o que estiver de fato validado. Reprovações voltam a
entrega ao Dev com feedback específico e acionável.
"""
from __future__ import annotations

from ..config import QA_MODEL
from ..tools import file_tools, test_tools
from ..tools.schemas import QA_TOOLS
from .base_agent import BaseAgent
from .utils import extract_json

SYSTEM_PROMPT = """\
Você é o QA de um squad autônomo de agentes de software. Você intercepta cada
entrega do Dev antes que ela seja considerada concluída.

Regras de trabalho:
1. Releia os critérios de aceite da story e a lista de arquivos alterados
   pelo Dev (use read_file para inspecionar o código de fato, não confie
   apenas no resumo do Dev).
2. Rode run_backend_tests (e run_frontend_tests se houver frontend) para
   validar que a suíte de testes automatizados passa - isso cobre a camada de
   integração. Trate falhas de teste como reprovação automática.
3. Faça um code review objetivo: identifique bugs, critérios de aceite não
   atendidos, ou riscos óbvios (ex: falta de validação de entrada em
   funcionalidade voltada a chão de fábrica).
4. Você só aprova quando TODOS os critérios de aceite estiverem
   demonstravelmente atendidos e os testes passarem. Na dúvida, reprove com
   feedback específico e acionável - liste exatamente o que falhou e o que
   precisa mudar, para o Dev poder corrigir sem adivinhar.

Ao concluir, responda SOMENTE com um objeto JSON (sem texto antes ou depois):
{
  "approved": true | false,
  "test_cases": [
    {"name": "nome do caso de teste", "result": "pass" | "fail", "notes": "observação"}
  ],
  "evidence": "resumo das evidências que sustentam a decisão (saída de testes, trechos revisados)",
  "feedback": "se reprovado, o que exatamente o Dev precisa corrigir; se aprovado, pode ser um resumo breve"
}
"""


class QAAgent(BaseAgent):
    name = "qa"
    model = QA_MODEL
    system_prompt = SYSTEM_PROMPT

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return file_tools.read_file(tool_input.get("rel_path", ""))
        if tool_name == "list_dir":
            return file_tools.list_dir(tool_input.get("rel_path", "."))
        if tool_name == "run_backend_tests":
            return test_tools.run_backend_tests(tool_input.get("rel_path", "backend"))
        if tool_name == "run_frontend_tests":
            return test_tools.run_frontend_tests(tool_input.get("rel_path", "frontend"))
        return f"[erro] ferramenta desconhecida: {tool_name}"

    @staticmethod
    def _find_story(backlog: list[dict], story_id: str | None) -> dict | None:
        return next((s for s in backlog if s["id"] == story_id), None)

    def _build_prompt(self, story: dict, decision: dict) -> str:
        return (
            f"User story {story['id']}: {story['title']}\n"
            f"{story['description']}\n\n"
            "Critérios de aceite:\n"
            + "\n".join(f"- {c}" for c in story["acceptance_criteria"])
            + "\n\nEntrega do Dev:\n"
            f"Resumo: {decision['summary']}\n"
            f"Justificativa técnica: {decision['rationale']}\n"
            f"Arquivos alterados: {', '.join(decision['files_changed']) or '(nenhum informado)'}\n"
            f"Testes escritos pelo Dev: {', '.join(decision['tests_written']) or '(nenhum informado)'}\n\n"
            "Faça o code review, execute os testes e responda com o JSON de veredito."
        )

    def run(self, state: dict) -> dict:
        story = self._find_story(state["backlog"], state["current_story_id"])
        if story is None:
            raise ValueError(f"Story não encontrada no backlog: {state['current_story_id']}")
        decision = state["decision_log"][-1]

        user = self._build_prompt(story, decision)
        raw, _transcript = self.call_with_tools(user, QA_TOOLS, self._execute_tool, max_iterations=15)
        result = extract_json(raw)
        result["story_id"] = story["id"]
        result.setdefault("test_cases", [])

        self.append_jsonl_artifact("qa_report.jsonl", result)

        next_recipient = "po" if result["approved"] else "dev"
        updates = {
            "qa_report": [result],
            "communication_log": [self.message(next_recipient, result["feedback"])],
        }
        if not result["approved"]:
            updates["revision_count"] = state["revision_count"] + 1
        return updates
