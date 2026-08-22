"""Dev Agent: implementa uma user story por vez em code/app.

Recebe a story ativa (e, em caso de retrabalho, o feedback do QA sobre a
tentativa anterior). Tem acesso de leitura e escrita a code/app e pode rodar a
suíte de testes de backend para validar seu próprio trabalho antes de entregar
ao QA. Toda decisão técnica relevante é registrada com justificativa.
"""
from __future__ import annotations

from .. import simple_project
from ..config import DEV_MODEL
from ..tools import file_tools, test_tools
from ..tools.schemas import DEV_TOOLS
from .base_agent import BaseAgent
from .utils import extract_json

SYSTEM_PROMPT = """\
Você é o Desenvolvedor de um squad autônomo de agentes de software. Você
consome uma user story escrita pelo PO (com critérios de aceite) e a
implementa dentro de code/app, que é a raiz da aplicação.

Regras de trabalho:
1. Antes de escrever código, use list_dir/read_file para entender a estrutura
   já existente em code/app e seguir os padrões e convenções já estabelecidos
   (linguagem, framework, organização de pastas). Se a aplicação ainda estiver
   vazia, use a arquitetura mais simples possível para a demo: backend HTTP em
   Python puro (biblioteca padrão), frontend estático em HTML/CSS/JS e dados em
   memória sem banco. Evite dependências externas, Docker e build de frontend.
2. Implemente a story por completo, incluindo testes unitários para a lógica
   nova ou alterada. Os testes de backend devem rodar com pytest a partir de
   code/app/backend.
3. Rode os testes com a ferramenta run_backend_tests antes de finalizar.
   Só entregue quando os testes passarem (exit_code=0). Se falharem, corrija
   e rode novamente.
4. Escreva código seguindo boas práticas (nomes claros, sem duplicação
   desnecessária, tratamento de erros nas bordas do sistema). Não adicione
   funcionalidades além do que a story pede.
5. Se você estiver recebendo feedback de uma rejeição do QA, corrija
   especificamente os pontos apontados - não reescreva tudo do zero.

Ao concluir, responda SOMENTE com um objeto JSON (sem texto antes ou depois):
{
  "summary": "o que foi implementado, em 1-3 frases",
  "rationale": "principais decisões técnicas tomadas e por quê",
  "files_changed": ["caminhos relativos a code/app dos arquivos criados/alterados"],
  "tests_written": ["nomes ou caminhos dos testes unitários escritos"]
}
"""


class DevAgent(BaseAgent):
    name = "dev"
    model = DEV_MODEL
    system_prompt = SYSTEM_PROMPT

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return file_tools.read_file(tool_input.get("rel_path", ""))
        if tool_name == "list_dir":
            return file_tools.list_dir(tool_input.get("rel_path", "."))
        if tool_name == "write_file":
            return file_tools.write_file(tool_input.get("rel_path", ""), tool_input.get("content", ""))
        if tool_name == "run_backend_tests":
            return test_tools.run_backend_tests(tool_input.get("rel_path", "backend"))
        return f"[erro] ferramenta desconhecida: {tool_name}"

    @staticmethod
    def _find_story(backlog: list[dict], story_id: str | None) -> dict | None:
        return next((s for s in backlog if s["id"] == story_id), None)

    def _build_prompt(self, story: dict, feedback: str | None) -> str:
        parts = [
            f"User story {story['id']}: {story['title']}",
            story["description"],
            "Critérios de aceite:",
            *[f"- {c}" for c in story["acceptance_criteria"]],
        ]
        if feedback:
            parts += [
                "",
                "ATENÇÃO: esta é uma retrabalho. O QA rejeitou a entrega anterior "
                "desta story com o seguinte feedback - corrija especificamente isso:",
                feedback,
            ]
        parts.append("\nImplemente a story em code/app e responda com o JSON de decisão.")
        return "\n".join(parts)

    def run(self, state: dict) -> dict:
        story = self._find_story(state["backlog"], state["current_story_id"])
        if story is None:
            raise ValueError(f"Story não encontrada no backlog: {state['current_story_id']}")

        if self.simple_mode:
            files_changed = []
            if story["id"] == state["backlog"][0]["id"]:
                for rel_path, content in simple_project.FILES.items():
                    file_tools.write_file(rel_path, content)
                    files_changed.append(rel_path)
            decision = {
                "story_id": story["id"],
                "summary": f"Story {story['id']} implementada pela arquitetura simples gerada pelo pipeline.",
                "rationale": "Usado backend Python puro, frontend estatico e dados em memoria para manter a demo reprodutivel.",
                "files_changed": files_changed,
                "tests_written": ["backend/test_app.py"] if files_changed else [],
            }
            self.append_jsonl_artifact("decision_log.jsonl", decision)
            return {
                "decision_log": [decision],
                "status": "in_qa",
                "communication_log": [self.message("qa", decision["summary"] + " | Justificativa: " + decision["rationale"])],
            }

        feedback = None
        if state["qa_report"]:
            last_qa = state["qa_report"][-1]
            if last_qa["story_id"] == story["id"] and not last_qa["approved"]:
                feedback = last_qa["feedback"]

        user = self._build_prompt(story, feedback)
        raw, transcript = self.call_with_tools(user, DEV_TOOLS, self._execute_tool, max_iterations=20)
        try:
            decision = extract_json(raw)
        except ValueError:
            written_files = [
                step["input"].get("rel_path", "")
                for step in transcript
                if step.get("step") == "tool_call" and step.get("name") == "write_file"
            ]
            decision = {
                "summary": "A story foi executada via ferramentas, mas o Dev nao retornou o JSON final esperado.",
                "rationale": "O pipeline registrou uma decisao automatica para manter a orquestracao auditavel.",
                "files_changed": [path for path in written_files if path],
                "tests_written": [path for path in written_files if "test" in path.lower()],
            }
        decision["story_id"] = story["id"]
        decision.setdefault("files_changed", [])
        decision.setdefault("tests_written", [])

        self.append_jsonl_artifact("decision_log.jsonl", decision)

        return {
            "decision_log": [decision],
            "status": "in_qa",
            "communication_log": [self.message("qa", decision["summary"] + " | Justificativa: " + decision["rationale"])],
        }
