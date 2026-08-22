"""Monta o resumo textual de execuções anteriores que vira `brief_history` no
SquadState - é o que faz o BriefingAnalyst tratar a 2a+ execução como um
incremento sobre o que já existe em code/app, em vez de reconstruir do zero."""
from __future__ import annotations


async def build_history_context(container, limit: int = 10) -> str:
    runs = await container.run_repo.list_recent(limit=limit)
    if not runs:
        return ""

    lines = ["Histórico de execuções anteriores do squad sobre esta mesma aplicação (mais recente primeiro):"]
    for run in runs:
        stories = await container.story_repo.list_by_run(run.id)
        approved = sum(1 for s in stories if s.status == "approved")
        excerpt = " ".join(run.raw_briefing.split())[:160]
        lines.append(
            f"- Run {run.id[:8]} ({run.created_at}): \"{excerpt}\" -> "
            f"status={run.status.value}, {len(stories)} stories, {approved} aprovadas."
        )
    return "\n".join(lines)
