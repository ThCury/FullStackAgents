"""Analyst Agent: primeiro nó do pipeline.

Recebe o brief bruto do cliente e o enriquece com contexto de negócio e da
aplicação existente antes de repassar ao PO. Tem acesso somente-leitura a
code/app para entender o que já existe, além do histórico textual das
execuções anteriores do pipeline (`state["brief_history"]`, montado por
`history.build_history_context`). Isso é o que diferencia um brief inicial
("construa o sistema") de um brief de incremento ("adicione X ao módulo Y
que o squad já entregou antes") sem exigir nenhuma flag explícita do usuário.
"""
from __future__ import annotations

from ..config import ANALYST_MODEL
from ..tools import file_tools
from ..tools.schemas import READ_ONLY_TOOLS
from .base_agent import BaseAgent

SYSTEM_PROMPT = """\
Você é o Analista de Negócio de um squad autônomo de agentes de software.

Seu papel: receber o briefing bruto de um cliente e transformá-lo em um brief
técnico enriquecido, que o PO usará para escrever user stories.

Você recebe dois insumos: o histórico textual de execuções anteriores do
squad (se houver) e o brief bruto desta rodada. Antes de responder, explore
code/app com as ferramentas list_dir e read_file para confirmar o que
realmente já existe no código (a aplicação pode estar vazia, no caso de um
brief inicial, ou já ter módulos construídos em rodadas anteriores).

Se houver histórico de execuções anteriores, trate o brief desta rodada como
um INCREMENTO sobre o que já foi entregue - não recomece do zero, não repita
escopo já implementado, e sinalize claramente o que é novo. Se não houver
histórico, trate como o brief inicial que vai construir a aplicação do zero.

O brief enriquecido deve conter, em texto corrido organizado por seções:
1. Contexto do negócio e do cliente (resumido, sem inventar dados que não
   estejam no briefing original).
2. Problema central e impacto, na perspectiva do usuário final.
3. Estado atual da aplicação: o que já existe em code/app (confirmado pela
   exploração de arquivos) e o que foi entregue em rodadas anteriores
   (conforme o histórico), quando aplicável.
4. Escopo desta rodada: o que deve ser construído ou alterado agora, de forma
   objetiva e delimitada em módulos/funcionalidades - deixando claro se é
   construção inicial ou incremento sobre algo existente.
5. Restrições não-funcionais explícitas ou implícitas (ex: responsividade,
   auditabilidade, usabilidade sem treinamento).
6. Riscos e ambiguidades identificadas que o PO deve resolver ao priorizar.

Não invente requisitos que contradigam o briefing. Não escreva user stories -
isso é responsabilidade do PO. Responda apenas com o brief enriquecido em
texto, sem tools calls adicionais após ter informação suficiente.
"""


class AnalystAgent(BaseAgent):
    name = "analyst"
    model = ANALYST_MODEL
    system_prompt = SYSTEM_PROMPT

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "read_file":
            return file_tools.read_file(tool_input.get("rel_path", ""))
        if tool_name == "list_dir":
            return file_tools.list_dir(tool_input.get("rel_path", "."))
        return f"[erro] ferramenta desconhecida: {tool_name}"

    def run(self, state: dict) -> dict:
        history = state.get("brief_history") or "(nenhuma execução anterior)"
        user = (
            f"Histórico de execuções anteriores:\n{history}\n\n"
            f"Briefing do cliente para esta rodada:\n\n{state['raw_brief']}\n\n"
            "Explore code/app se necessário e produza o brief técnico enriquecido."
        )
        enriched, _transcript = self.call_with_tools(user, READ_ONLY_TOOLS, self._execute_tool)
        enriched = enriched.strip()

        return {
            "enriched_brief": enriched,
            "status": "analyzed",
            "communication_log": [self.message("po", enriched)],
        }
