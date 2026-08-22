"""Ponto de entrada do pipeline: recebe um brief e executa o squad completo.

O primeiro brief recebido constrói a aplicação em code/app do zero. Qualquer
brief seguinte é tratado como um incremento sobre o que já foi entregue -
o Analyst enxerga tanto o código atual em code/app quanto o histórico textual
das execuções anteriores (ver history.py) para decidir o que já existe e o
que precisa ser adicionado ou alterado.

Uso via CLI:
    python -m pipeline.run --brief-file pipeline/briefs/rivexx.txt
    python -m pipeline.run --brief "texto do brief aqui"
    python -m pipeline.run --interactive   # modo conversacional: brief inicial
                                            # e incrementos, um por vez

Uso programático (ex: a partir de uma API futura):
    from pipeline.run import run_pipeline
    result = run_pipeline(brief_text)
"""
from __future__ import annotations

import argparse
import json

from . import history
from .graph import build_graph
from .state import PipelineState, initial_state


def run_pipeline(brief: str, max_revisions: int | None = None) -> PipelineState:
    run_dir, index, timestamp = history.start_run()
    (run_dir / "brief.txt").write_text(brief, encoding="utf-8")

    app = build_graph(run_dir=run_dir)
    state = initial_state(brief, max_revisions=max_revisions)
    state["brief_history"] = history.build_history_context()

    final_state = app.invoke(state, config={"recursion_limit": 100})

    (run_dir / "enriched_brief.txt").write_text(final_state.get("enriched_brief", ""), encoding="utf-8")
    (run_dir / "communication_log.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in final_state["communication_log"]),
        encoding="utf-8",
    )
    history.write_summary(run_dir, index, timestamp, brief, final_state)
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


def _read_multiline_brief() -> str | None:
    """Lê um brief de múltiplas linhas do terminal, finalizado por uma linha
    em branco. Retorna None em EOF/Ctrl+D para sinalizar saída do loop."""
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            return None
        if line == "":
            if lines:
                break
            continue
        lines.append(line)
    return "\n".join(lines)


def _interactive_loop(max_revisions: int | None = None) -> None:
    print("Squad de agentes - modo interativo.")
    print(
        "A primeira mensagem constrói o sistema em code/app; as próximas são "
        "tratadas como incremento sobre o que já foi entregue."
    )
    print("Digite o brief (uma ou mais linhas) e finalize com uma linha em branco. Ctrl+D para sair.\n")

    while True:
        print("brief> ", end="", flush=True)
        brief = _read_multiline_brief()
        if brief is None:
            print("\nEncerrando.")
            return
        if not brief.strip():
            continue

        print("\n--- squad trabalhando ---")
        result = run_pipeline(brief, max_revisions=max_revisions)
        _print_summary(result)
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o squad de agentes sobre um brief de cliente.")
    parser.add_argument("--brief", type=str, help="Texto do brief.")
    parser.add_argument("--brief-file", type=str, help="Arquivo texto com o brief.")
    parser.add_argument(
        "--interactive", action="store_true",
        help="Modo conversacional: pede um brief por vez no terminal (inicial e incrementos).",
    )
    parser.add_argument("--max-revisions", type=int, default=None, help="Máximo de retrabalhos por story antes de escalar.")
    args = parser.parse_args()

    if args.interactive:
        _interactive_loop(max_revisions=args.max_revisions)
        return

    if args.brief_file:
        from pathlib import Path

        brief = Path(args.brief_file).read_text(encoding="utf-8")
    elif args.brief:
        brief = args.brief
    else:
        parser.error("Informe --brief, --brief-file ou --interactive")
        return

    result = run_pipeline(brief, max_revisions=args.max_revisions)
    _print_summary(result)


if __name__ == "__main__":
    main()
