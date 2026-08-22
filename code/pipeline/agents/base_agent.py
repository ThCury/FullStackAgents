"""Classe base dos agentes: encapsula cliente Anthropic, loop agentic de
tool-use e persistência de artefatos auditáveis (backlog, decisões, QA, log
de comunicação).

Cada agente concreto (Analyst, PO, Dev, QA) é responsável por sua própria
construção e configuração (modelo, prompt de sistema, tools disponíveis).
O grafo do pipeline (graph.py) apenas instancia a classe e chama `.run(state)`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import anthropic

from .. import config


class BaseAgent:
    name: str = "agent"
    model: str = config.DEFAULT_MODEL
    system_prompt: str = ""

    def __init__(self, model: str | None = None, run_dir: Path | None = None):
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada. Defina a variável de ambiente "
                "ou crie um arquivo .env em code/pipeline (veja .env.example)."
            )
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        if model:
            self.model = model
        # Diretório de artefatos da execução atual (pipeline/artifacts/runs/NNN_...).
        # Cai no diretório flat de artifacts/ quando o agente é usado fora de uma
        # execução do grafo (ex: testes manuais).
        self.run_dir = run_dir or config.ARTIFACTS_DIR

    # -- comunicação com o LLM -------------------------------------------------

    def call(self, user: str, system: str | None = None, max_tokens: int = 4096) -> str:
        """Chamada simples sem tools."""
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or self.system_prompt,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    def call_with_tools(
        self,
        user: str,
        tools: list[dict],
        tool_executor: Callable[[str, dict], str],
        system: str | None = None,
        max_iterations: int = config.MAX_TOOL_ITERATIONS,
        max_tokens: int = 4096,
        validate_final: Callable[[str], bool] | None = None,
        invalid_final_message: str = (
            "Sua última resposta não veio no formato esperado. Responda agora "
            "apenas com o conteúdo solicitado, exatamente como instruído, sem "
            "chamar ferramentas."
        ),
    ) -> tuple[str, list[dict]]:
        """Loop agentic: chama o modelo, executa tool calls, repete até obter
        uma resposta final em texto (sem tool_use) ou atingir max_iterations.

        `validate_final`, se informado, decide se o texto final "conta" como
        resposta válida (ex: contém um JSON parseável). Quando o modelo
        termina o turno sem tool_use mas com um texto vazio ou que falha na
        validação - o que acontece ocasionalmente após uma sequência longa de
        tool calls, seja com conteúdo vazio ou com prosa em vez do formato
        pedido -, em vez de devolver esse texto (o que quebraria o parsing
        downstream e mataria o pipeline inteiro) pedimos explicitamente para
        tentar de novo, com orçamento limitado de tentativas.

        Retorna (texto_final, transcript) onde transcript é a lista de passos
        (texto intermediário + chamadas de ferramenta) para fins de auditoria.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        transcript: list[dict] = []
        invalid_retries = 0
        max_invalid_retries = 2

        for _ in range(max_iterations):
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or self.system_prompt,
                tools=tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})

            texts = [b.text for b in resp.content if b.type == "text"]
            tool_uses = [b for b in resp.content if b.type == "tool_use"]

            if texts:
                transcript.append({"step": "assistant_text", "content": "\n".join(texts)})

            if not tool_uses:
                final_text = "\n".join(texts).strip()
                is_valid = bool(final_text) and (validate_final is None or validate_final(final_text))
                if is_valid:
                    return final_text, transcript

                invalid_retries += 1
                transcript.append({"step": "invalid_final_retry", "attempt": invalid_retries})
                if invalid_retries > max_invalid_retries:
                    return final_text, transcript
                messages.append({"role": "user", "content": invalid_final_message})
                continue

            tool_results = []
            for tu in tool_uses:
                try:
                    result = tool_executor(tu.name, tu.input)
                except Exception as exc:  # nunca deixar o loop morrer por erro de tool
                    result = f"[erro ao executar {tu.name}] {exc}"
                transcript.append(
                    {"step": "tool_call", "name": tu.name, "input": tu.input, "result": str(result)[:2000]}
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id, "content": str(result)}
                )
            messages.append({"role": "user", "content": tool_results})

        transcript.append({"step": "max_iterations_reached"})
        return "[o agente atingiu o número máximo de iterações de ferramentas]", transcript

    # -- comunicação auditável entre agentes ------------------------------------

    def message(self, to_agent: str, content: str) -> dict:
        return {"from_agent": self.name, "to_agent": to_agent, "content": content, "ts": time.time()}

    # -- persistência de artefatos ------------------------------------------

    def _artifacts_path(self, filename: str) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir / filename

    def write_json_artifact(self, filename: str, data: Any) -> None:
        self._artifacts_path(filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def append_jsonl_artifact(self, filename: str, entry: dict) -> None:
        path = self._artifacts_path(filename)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
