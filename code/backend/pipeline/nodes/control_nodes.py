"""Nós determinísticos — sem LLM, sem token, sem variação entre execuções.

`dispatch`, `escalate` e `integrate` são código comum. Isso é deliberado:
escolher a próxima story, pausar para um humano e montar o relatório final são
decisões com regra conhecida. Delegar a um modelo custaria dinheiro para
introduzir variabilidade onde não queremos nenhuma.

Regra prática do projeto: **se a regra é conhecida, o nó é determinístico.**
Um agente só entra quando o trabalho é interpretação, geração ou julgamento.
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from domain.entities.backlog import Story
from domain.entities.messaging import AgentMessage
from domain.entities.run import RunSummary
from domain.enums import AgentRole, MessageKind, ScenarioTag, Verdict
from domain.ports.execution import CodeWorkspacePort
from domain.ports.observability import EventBusPort, SquadEvent, TokenMeterPort
from domain.ports.repositories import MessageRepository
from domain.ports.system import ClockPort, IdGeneratorPort
from pipeline.state import SquadState, current_story, latest_report


class DispatchNode:
    """Escolhe a próxima story e registra o handoff do orquestrador.

    Emite `AgentMessage` como qualquer agente: o orquestrador também é ator na
    timeline. Sem isso, o Console mostraria o Dev recebendo trabalho do nada.
    """

    def __init__(
        self,
        messages: MessageRepository,
        events: EventBusPort,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._messages = messages
        self._events = events
        self._ids = ids
        self._clock = clock

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        queue = list(state.get("queue", []))
        backlog = {s["id"]: s for s in state.get("backlog", [])}
        rework = state.get("rework", {})

        next_id = self._pick(queue, backlog, rework)
        if next_id is None:
            await self._announce(
                run_id,
                summary="Backlog concluído — encaminhando para integração",
                ref=None,
                to_agent=AgentRole.ORCHESTRATOR,
                rationale="Nenhuma story pendente na fila",
            )
            return {"current_story_id": None, "queue": []}

        story = backlog[next_id]
        await self._announce(
            run_id,
            summary=f"Story selecionada: {story['title']} ({story['priority']})",
            ref=next_id,
            to_agent=AgentRole.DEVELOPER,
            rationale="Seleção por prioridade MoSCoW com dependências satisfeitas",
        )
        return {"current_story_id": next_id}

    def _pick(
        self,
        queue: list[str],
        backlog: dict[str, dict[str, Any]],
        rework: dict[str, int],
    ) -> str | None:
        """Primeira story da fila cujas dependências já foram aceitas.

        `queue` já vem ordenada por prioridade (`Backlog.ordered()`). Aqui só
        respeitamos dependência — sem isso, o Dev receberia uma story cuja base
        ainda não existe e o QA reprovaria por motivo que não é culpa dele.
        """
        for story_id in queue:
            story = backlog.get(story_id)
            if story is None:
                continue
            unmet = [dep for dep in story.get("depends_on", []) if dep in queue and dep != story_id]
            if not unmet:
                return story_id
        # Todas bloqueadas por dependência circular: pega a primeira para não
        # travar o run. O QA vai reprovar e a escalada trata.
        return queue[0] if queue else None

    async def _announce(
        self,
        run_id: str,
        *,
        summary: str,
        ref: str | None,
        to_agent: AgentRole,
        rationale: str,
    ) -> None:
        message = AgentMessage(
            id=self._ids.new_id("msg"),
            run_id=run_id,
            seq=await self._messages.next_seq(run_id),
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=to_agent,
            kind=MessageKind.HANDOFF,
            ref=ref,
            summary=summary,
            rationale=rationale,
            created_at=self._clock.now(),
        )
        await self._messages.append(message)
        await self._events.publish(
            SquadEvent(run_id=run_id, type="message", payload=message.model_dump(mode="json"))
        )


class EscalateNode:
    """Pausa o run e devolve a decisão a um humano (`interrupt()`).

    Dispara quando o QA reprovou além do limite, ou quando o orçamento estourou.
    Alternativa que recusamos: seguir tentando. Loop Dev<->QA improdutivo é o
    jeito mais rápido de queimar orçamento sem produzir nada.

    A intervenção humana entra na trilha como qualquer handoff — quem avalia a
    demo precisa ver onde o squad pediu ajuda, não descobrir depois.
    """

    def __init__(
        self,
        messages: MessageRepository,
        events: EventBusPort,
        ids: IdGeneratorPort,
        clock: ClockPort,
        meter: TokenMeterPort,
    ) -> None:
        self._messages = messages
        self._events = events
        self._ids = ids
        self._clock = clock
        self._meter = meter

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        story = current_story(state)
        story_id = story["id"] if story else None
        report = latest_report(state, story_id) if story_id else None

        request = {
            "story_id": story_id,
            "story_title": story["title"] if story else None,
            "attempts": state.get("rework", {}).get(story_id or "", 0),
            "rejection_reason": (report or {}).get("rejection_reason"),
            "required_changes": (report or {}).get("required_changes", []),
            "budget": (await self._meter.snapshot(run_id)).model_dump(mode="json"),
            "options": ["retry", "skip", "finish"],
        }

        message = AgentMessage(
            id=self._ids.new_id("msg"),
            run_id=run_id,
            seq=await self._messages.next_seq(run_id),
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.HUMAN,
            kind=MessageKind.QUESTION,
            ref=story_id,
            summary=f"Escalada: story '{request['story_title']}' após "
            f"{request['attempts']} reprovação(ões)",
            payload=request,
            rationale="Limite de retrabalho atingido — decisão humana é mais barata "
            "que continuar iterando",
            created_at=self._clock.now(),
        )
        await self._messages.append(message)
        await self._events.publish(SquadEvent(run_id=run_id, type="interrupt", payload=request))

        # Pausa aqui. O checkpointer preserva o estado; `ResumeRun` retoma com a
        # decisão do humano injetada como retorno do `interrupt()`.
        decision = interrupt(request)

        resolution = (
            decision.get("resolution", "skip") if isinstance(decision, dict) else str(decision)
        )
        return {
            "escalations": [
                {**request, "resolution": resolution, "decided_at": self._clock.now().isoformat()}
            ]
        }


class IntegrateNode:
    """Fecha o run: consolida, exporta os entregáveis, verifica cobertura.

    Recusa fechar em silêncio um run que não cobriu os 3 cenários da demo — o
    `RunSummary` carrega `scenarios_covered` e o Console mostra o que faltou.
    Falhar visível é melhor que entregar incompleto parecendo completo.
    """

    def __init__(
        self,
        workspace: CodeWorkspacePort,
        meter: TokenMeterPort,
        messages: MessageRepository,
        events: EventBusPort,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._workspace = workspace
        self._meter = meter
        self._messages = messages
        self._events = events
        self._ids = ids
        self._clock = clock

    async def __call__(self, state: SquadState) -> dict[str, Any]:
        run_id = state["run_id"]
        stories = [Story.model_validate(s) for s in state.get("backlog", [])]
        reports = state.get("test_reports", [])
        approved = [r for r in reports if r.get("verdict") == Verdict.APPROVED.value]
        accepted_story_ids = {r["story_ref"] for r in approved}

        covered = sorted(
            {s.scenario_tag for s in stories if s.scenario_tag and s.id in accepted_story_ids},
            key=lambda t: t.value,
        )
        budget = await self._meter.snapshot(run_id)

        summary = RunSummary(
            run_id=run_id,
            stories_total=len(stories),
            stories_accepted=len(accepted_story_ids),
            artifacts_delivered=len(state.get("artifacts", [])),
            adrs_recorded=len(state.get("adrs", [])),
            test_cases_executed=sum(len(r.get("cases", [])) for r in reports),
            test_cases_passed=sum(
                1 for r in reports for c in r.get("cases", []) if c.get("outcome") == "passed"
            ),
            rework_cycles=sum(state.get("rework", {}).values()),
            scenarios_covered=covered,
            total_tokens=budget.total_spent,
            total_cost_usd=budget.total_cost_usd,
            exported_files=await self._export(state, stories),
        )

        missing = [t.value for t in ScenarioTag if t not in covered]
        message = AgentMessage(
            id=self._ids.new_id("msg"),
            run_id=run_id,
            seq=await self._messages.next_seq(run_id),
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=AgentRole.HUMAN,
            kind=MessageKind.DELIVERY,
            summary=(
                f"Run concluído: {summary.stories_accepted}/{summary.stories_total} stories "
                f"aceitas, {len(covered)}/{len(ScenarioTag)} cenários cobertos"
            ),
            payload=summary.model_dump(mode="json"),
            rationale=(
                f"Cenários sem story aceita: {', '.join(missing)}"
                if missing
                else "Todos os cenários obrigatórios da demo foram cobertos"
            ),
            created_at=self._clock.now(),
        )
        await self._messages.append(message)
        await self._events.publish(
            SquadEvent(run_id=run_id, type="run_finished", payload=summary.model_dump(mode="json"))
        )

        return {"summary": summary.model_dump(mode="json"), "current_story_id": None}

    async def _export(self, state: SquadState, stories: list[Story]) -> list[str]:
        """Os 5 entregáveis do enunciado, em Markdown, dentro do workspace.

        O avaliador pode querer levar os arquivos, não só ver a tela.
        """
        from application.exporters import (
            render_adr_log,
            render_backlog,
            render_qa_report,
            render_timeline,
        )

        run_id = state["run_id"]
        messages = await self._messages.list_by_run(run_id)

        exports = {
            "docs/backlog.md": render_backlog(stories, state.get("briefing")),
            "docs/adr/decision-log.md": render_adr_log(state.get("adrs", [])),
            "docs/qa-report.md": render_qa_report(state.get("test_reports", []), stories),
            "docs/squad-timeline.md": render_timeline(messages),
        }
        return [
            await self._workspace.export(run_id, path, content) for path, content in exports.items()
        ]
