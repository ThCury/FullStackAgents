"""Ponto de entrada do pipeline: recebe um brief e executa o squad completo.

Uso via CLI:
    python -m pipeline.run --brief-file pipeline/briefs/rivexx.txt
    python -m pipeline.run --brief "texto do brief aqui"

Uso programático (ex: a partir de uma API):
    from pipeline.run import run_pipeline
    result = run_pipeline(brief_text)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .graph import build_graph
from .state import PipelineState, initial_state


def run_pipeline(brief: str, max_revisions: int | None = None) -> PipelineState:
    app = build_graph()
    state = initial_state(brief, max_revisions=max_revisions)
    final_state = app.invoke(state, config={"recursion_limit": 100})

    from . import config

    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.ARTIFACTS_DIR / "communication_log.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in final_state["communication_log"]),
        encoding="utf-8",
    )
    return final_state


def _print_summary(result: PipelineState) -> None:
    print(json.dumps(
        {
            "status": result.get("status"),
            "stories": len(result.get("backlog", [])),
            "decisions": len(result.get("decision_log", [])),
            "qa_results": [
                {"story_id": r["story_id"], "approved": r["approved"]} for r in result.get("qa_report", [])
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o squad de agentes sobre um brief de cliente.")
    parser.add_argument("--brief", type=str, help="Texto do brief.")
    parser.add_argument("--brief-file", type=str, help="Arquivo texto com o brief.")
    parser.add_argument("--max-revisions", type=int, default=None, help="Máximo de retrabalhos por story antes de escalar.")
    args = parser.parse_args()

    if args.brief_file:
        brief = Path(args.brief_file).read_text(encoding="utf-8")
    elif args.brief:
        brief = args.brief
    else:
        parser.error("Informe --brief ou --brief-file")
        return

    result = run_pipeline(brief, max_revisions=args.max_revisions)
    _print_summary(result)


if __name__ == "__main__":
    main()
