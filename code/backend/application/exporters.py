"""Renderizadores dos 5 entregáveis da Trilha B em Markdown.

Ficam em `application/` e não em `interfaces/` porque não são apresentação de
uma tela: são artefatos de saída do run, gravados no workspace e consumíveis
fora do Console.

Funções puras, sem I/O — quem grava é a `CodeWorkspacePort`. Isso as torna
testáveis por comparação de string e reutilizáveis por qualquer canal (arquivo,
endpoint, download no Console).
"""

from __future__ import annotations

from typing import Any

from domain.entities.backlog import Story
from domain.entities.messaging import AgentMessage
from domain.enums import Verdict


def render_backlog(stories: list[Story], briefing: dict[str, Any] | None) -> str:
    lines = ["# Backlog — gerado pelo PO Agent", ""]

    if briefing:
        lines += [
            f"**Cliente:** {briefing.get('company', '—')}",
            "",
            "## Perguntas abertas levantadas pelo Briefing Analyst",
            "",
        ]
        questions = briefing.get("open_questions", [])
        lines += (
            [f"- **{q['question']}** — {q['why_it_matters']}" for q in questions]
            if questions
            else ["_Nenhuma ambiguidade bloqueante detectada._"]
        )
        lines.append("")

    lines += ["## Stories", ""]
    for story in stories:
        tag = story.scenario_tag.value if story.scenario_tag else "—"
        lines += [
            f"### `{story.id}` {story.title}",
            "",
            f"- **Prioridade:** {story.priority.value.upper()}",
            f"- **Cenário da demo:** {tag}",
            f"- **Status:** {story.status.value}",
            "",
            f"> {story.narrative}",
            "",
            f"**Por que esta prioridade:** {story.rationale}",
            "",
            "**Critérios de aceite:**",
            "",
        ]
        for crit in story.acceptance_criteria:
            lines += [f"- `{crit.id}`", "  ```gherkin", *_indent(crit.to_gherkin()), "  ```"]
        lines.append("")

    return "\n".join(lines)


def render_adr_log(adrs: list[dict[str, Any]]) -> str:
    lines = [
        "# Log de decisões técnicas — Dev Agent",
        "",
        "Cada decisão registra as alternativas consideradas. Justificativa sem",
        "alternativa é racionalização, não decisão.",
        "",
    ]
    if not adrs:
        lines.append("_Nenhuma decisão registrada._")
        return "\n".join(lines)

    for adr in adrs:
        alternatives = "\n".join(f"- {a}" for a in adr.get("alternatives_considered", []))
        lines += [
            f"## {adr['id']} — {adr['title']}",
            "",
            f"**Story:** `{adr['story_ref']}`",
            "",
            f"### Contexto\n{adr['context']}",
            "",
            f"### Decisão\n{adr['decision']}",
            "",
            f"### Alternativas consideradas\n{alternatives}",
            "",
            f"### Justificativa\n{adr['rationale']}",
            "",
            f"### Consequências\n{adr['consequences']}",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def render_qa_report(reports: list[dict[str, Any]], stories: list[Story]) -> str:
    titles = {s.id: s.title for s in stories}
    lines = [
        "# Relatório de QA — casos executados e evidências de aceite",
        "",
        "| Story | Tentativa | Veredito | Passou | Falhou |",
        "| --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        cases = report.get("cases", [])
        passed = sum(1 for c in cases if c.get("outcome") == "passed")
        failed = sum(1 for c in cases if c.get("outcome") == "failed")
        verdict = "✅ aprovada" if report["verdict"] == Verdict.APPROVED.value else "❌ reprovada"
        title = titles.get(report["story_ref"], report["story_ref"])
        lines.append(f"| {title} | {report.get('attempt', 1)} | {verdict} | {passed} | {failed} |")

    lines.append("")
    for report in reports:
        title = titles.get(report["story_ref"], report["story_ref"])
        lines += [
            f"## {title} — tentativa {report.get('attempt', 1)}",
            "",
            report.get("summary", ""),
            "",
        ]
        if report["verdict"] == Verdict.REJECTED.value:
            changes = "\n".join(f"- {c}" for c in report.get("required_changes", []))
            lines += [
                f"**Motivo da reprovação:** {report.get('rejection_reason', '—')}",
                "",
                f"**Mudanças requeridas:**\n{changes}",
                "",
            ]
        for case in report.get("cases", []):
            icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(case["outcome"], "?")
            evidence = ", ".join(e["kind"] for e in case.get("evidence", [])) or "—"
            lines += [
                f"### {icon} `{case['criterion_ref']}` {case['title']}",
                "",
                f"- **Esperado:** {case['expected']}",
                f"- **Obtido:** {case['actual']}",
                f"- **Evidência:** {evidence}",
                "",
            ]
    return "\n".join(lines)


def render_timeline(messages: list[AgentMessage]) -> str:
    """A trilha de comunicação entre os agentes.

    Este é o entregável que o enunciado trata como eliminatório: "um output
    final sem orquestração visível não será considerado".
    """
    lines = [
        "# Timeline do squad — comunicação entre agentes",
        "",
        f"{len(messages)} handoffs registrados.",
        "",
    ]
    for message in messages:
        lines += [
            f"## #{message.seq} {message.from_agent} → {message.to_agent} [{message.kind}]",
            "",
            f"**{message.summary}**",
            "",
        ]
        if message.rationale:
            lines += [f"_Justificativa:_ {message.rationale}", ""]
        if message.usage.total:
            lines += [
                f"_Tokens:_ {message.usage.total} "
                f"(entrada {message.usage.input_tokens}, saída {message.usage.output_tokens}) "
                f"— US$ {message.usage.cost_usd:.4f}",
                "",
            ]
    return "\n".join(lines)


def _indent(text: str, prefix: str = "  ") -> list[str]:
    return [f"{prefix}{line}" for line in text.splitlines()]
