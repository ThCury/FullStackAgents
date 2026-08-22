"""Versão em streaming do pipeline: mesmo fluxo de `run.run_pipeline`, mas
expõe cada mensagem nova do `communication_log` assim que o nó correspondente
termina, em vez de esperar o grafo inteiro rodar antes de devolver qualquer
coisa. Pensado para alimentar um endpoint SSE no backend.

O LangGraph, em `stream_mode="values"`, emite o estado acumulado completo após
cada nó. Aqui comparamos o tamanho do `communication_log` a cada passo com o
que já foi emitido e mandamos só as mensagens novas - o mesmo dado que
`run_pipeline` grava de uma vez em `communication_log.jsonl`, só que
incremental.
"""
from __future__ import annotations

import json
from typing import Iterator

from . import history
from .graph import build_graph
from .state import PipelineState, initial_state


def run_pipeline_stream(brief: str, max_revisions: int | None = None) -> Iterator[dict]:
    """Executa o squad e produz eventos incrementais.

    Cada item gerado é um dict `{"type": ..., "data": ...}`:
    - `{"type": "message", "data": Message}` para cada nova entrada do
      communication_log, na ordem em que os agentes as produzem.
    - `{"type": "done", "data": {...}}` uma única vez, ao final, com o mesmo
      resumo que `run._print_summary` imprime no modo CLI.

    Os artefatos em `artifacts/runs/<NNN>_<timestamp>/` são gravados da mesma
    forma que em `run_pipeline`, então uma execução via streaming fica
    indistinguível de uma via CLI para efeito de histórico/incremento.
    """
    run_dir, index, timestamp = history.start_run()
    (run_dir / "brief.txt").write_text(brief, encoding="utf-8")

    app = build_graph(run_dir=run_dir)
    state = initial_state(brief, max_revisions=max_revisions)
    state["brief_history"] = history.build_history_context()

    seen = 0
    final_state: PipelineState = state
    for step_state in app.stream(state, config={"recursion_limit": 100}, stream_mode="values"):
        final_state = step_state
        log = step_state.get("communication_log", [])
        while seen < len(log):
            yield {"type": "message", "data": log[seen]}
            seen += 1

    (run_dir / "enriched_brief.txt").write_text(final_state.get("enriched_brief", ""), encoding="utf-8")
    (run_dir / "communication_log.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in final_state["communication_log"]),
        encoding="utf-8",
    )
    token_usage = final_state.get("token_usage", [])
    (run_dir / "token_usage.jsonl").write_text(
        "\n".join(json.dumps(u, ensure_ascii=False) for u in token_usage),
        encoding="utf-8",
    )
    history.write_summary(run_dir, index, timestamp, brief, final_state)

    yield {
        "type": "done",
        "data": {
            "status": final_state.get("status"),
            "stories": len(final_state.get("backlog", [])),
            "decisions": len(final_state.get("decision_log", [])),
            "qa_results": [
                {"story_id": r["story_id"], "approved": r["approved"]}
                for r in final_state.get("qa_report", [])
            ],
            "total_input_tokens": sum(u.get("input_tokens", 0) for u in token_usage),
            "total_output_tokens": sum(u.get("output_tokens", 0) for u in token_usage),
        },
    }
