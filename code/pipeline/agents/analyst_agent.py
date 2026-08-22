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

from ..config import ANALYST_MAX_TOOL_ITERATIONS, ANALYST_MODEL
from ..tools import file_tools
from ..tools.schemas import READ_ONLY_TOOLS
from .base_agent import BaseAgent

SYSTEM_PROMPT = """\
Você é o Analista de Negócio de um squad autônomo de agentes de software.

Seu papel: receber o briefing bruto de um cliente e transformá-lo em um brief
técnico enriquecido, direto e sem redundância, que o PO usará para escrever
user stories.

Você recebe dois insumos: o histórico textual de execuções anteriores do
squad (se houver) e o brief bruto desta rodada. Antes de responder, explore
code/app com list_dir e read_file para confirmar o que realmente já existe no
código (pode estar vazio, no caso de um brief inicial, ou já ter módulos de
rodadas anteriores).

Se houver histórico, trate o brief desta rodada como um INCREMENTO sobre o
que já foi entregue - não recomece do zero, não repita escopo já
implementado, sinalize só o que é novo. Sem histórico, é o brief inicial que
constrói a aplicação do zero.

Responda em bullets curtos e objetivos, sem repetir o texto do briefing
original, organizados em 4 blocos - omita qualquer bloco sem conteúdo
relevante em vez de preenchê-lo de forma genérica:
1. Contexto e problema: negócio, usuário afetado e impacto - só o essencial,
   sem inventar dados que não estejam no briefing.
2. Estado atual: o que já existe em code/app (confirmado pela exploração) e
   o que rodadas anteriores já entregaram, se houver.
3. Escopo desta rodada: o que construir/alterar agora, delimitado em
   módulos/funcionalidades, deixando claro se é construção inicial ou
   incremento - inclua restrição não-funcional só se for relevante aqui.
4. Riscos e ambiguidades que o PO precisa resolver ao priorizar.

Não invente requisitos que contradigam o briefing. Não escreva user stories -
isso é responsabilidade do PO. Responda apenas com o brief enriquecido, sem
tool calls adicionais após ter informação suficiente.
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
        enriched, _transcript, _finished_cleanly = self.call_with_tools(
            user, READ_ONLY_TOOLS, self._execute_tool, max_iterations=ANALYST_MAX_TOOL_ITERATIONS
        )
        enriched = enriched.strip()

        return {
            "enriched_brief": enriched,
            "status": "analyzed",
            "communication_log": [self.message("po", enriched)],
            "token_usage": [self.usage_entry()],
        }
