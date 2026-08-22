"""Histórico persistente de execuções do pipeline.

Cada chamada a `run_pipeline` gera uma pasta própria em
`artifacts/runs/<indice>_<timestamp>/` com o brief recebido, o backlog gerado,
as decisões do Dev, o relatório do QA e o log de comunicação daquela rodada.

Isso é o que permite tratar a segunda (e demais) execução como um incremento:
`build_history_context` monta um resumo textual das rodadas anteriores que é
passado ao Analyst, para que ele saiba o que já foi pedido e entregue antes de
enriquecer o novo brief.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config


def _runs_dir() -> Path:
    d = config.ARTIFACTS_DIR / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_past_runs() -> list[dict]:
    runs = []
    for summary_path in _runs_dir().glob("*/summary.json"):
        try:
            runs.append(json.loads(summary_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(runs, key=lambda r: r["index"])


def start_run() -> tuple[Path, int, str]:
    """Cria o diretório da nova execução e retorna (run_dir, índice, timestamp)."""
    past = list_past_runs()
    index = (past[-1]["index"] + 1) if past else 1
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _runs_dir() / f"{index:03d}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, index, timestamp


def build_history_context(max_runs: int = 10) -> str:
    past = list_past_runs()
    if not past:
        return "(nenhuma execução anterior - este é o brief inicial, a aplicação em code/app ainda não existe)"
    lines = [
        "Histórico de execuções anteriores do squad sobre esta mesma aplicação "
        "(da mais antiga para a mais recente):"
    ]
    for run in past[-max_runs:]:
        lines.append(
            f"- Execução #{run['index']} ({run['timestamp']}): brief recebido - "
            f"\"{run['brief_excerpt']}\" -> status={run['status']}, "
            f"{run['story_count']} stories geradas, {run['approved_count']} aprovadas pelo QA."
        )
    return "\n".join(lines)


def write_summary(run_dir: Path, index: int, timestamp: str, brief: str, final_state: dict) -> None:
    token_usage = final_state.get("token_usage", [])
    summary = {
        "index": index,
        "timestamp": timestamp,
        "brief_excerpt": " ".join(brief.strip().split())[:160],
        "status": final_state.get("status"),
        "story_count": len(final_state.get("backlog", [])),
        "approved_count": sum(1 for r in final_state.get("qa_report", []) if r.get("approved")),
        "total_input_tokens": sum(u.get("input_tokens", 0) for u in token_usage),
        "total_output_tokens": sum(u.get("output_tokens", 0) for u in token_usage),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
