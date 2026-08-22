"""Casos de uso do ciclo de vida de um run.

Orquestram ports; não contêm regra de domínio nem detalhe de framework. Não há
um `import fastapi` aqui — é o que permite acionar o squad por HTTP, por CLI ou
por teste com o mesmo código.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from domain.entities.run import Run
from domain.enums import RunStatus
from domain.errors import (
    BudgetExceeded,
    DomainError,
    NoCheckpointAvailable,
    RunNotFound,
    RunNotRetryable,
)
from domain.ports.execution import CodeWorkspacePort
from domain.ports.observability import EventBusPort, SquadEvent, TokenMeterPort
from domain.ports.repositories import RunRepository
from domain.ports.system import ClockPort, IdGeneratorPort
from domain.value_objects import BudgetPolicy
from pipeline.state import initial_state

logger = logging.getLogger(__name__)


class StartRunUseCase:
    """Cria o run e dispara o grafo em background.

    Retorna imediatamente com o `Run` em `PENDING`: a execução leva minutos e o
    Console acompanha por SSE. Uma requisição HTTP que espera o squad terminar
    estoura qualquer timeout razoável.
    """

    def __init__(
        self,
        runs: RunRepository,
        workspace: CodeWorkspacePort,
        events: EventBusPort,
        ids: IdGeneratorPort,
        clock: ClockPort,
        graph: Any,
        policy: BudgetPolicy,
    ) -> None:
        self._runs = runs
        self._workspace = workspace
        self._events = events
        self._ids = ids
        self._clock = clock
        self._graph = graph
        self._policy = policy
        self._tasks: set[asyncio.Task[None]] = set()

    async def execute(self, briefing: str) -> Run:
        run = Run.create(
            run_id=self._ids.new_id("run"),
            briefing=briefing.strip(),
            policy=self._policy,
            now=self._clock.now(),
        )
        workspace_path = await self._workspace.prepare(run.id)
        run = run.model_copy(update={"workspace_path": workspace_path})
        await self._runs.save(run)

        # Referência forte à task: sem isso o GC pode coletar a task no meio da
        # execução, e o run morre sem erro visível.
        task = asyncio.create_task(self._drive(run), name=f"squad:{run.id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        return run

    async def _drive(self, run: Run) -> None:
        await self._runs.save(run.with_status(RunStatus.RUNNING, started_at=self._clock.now()))
        config = {"configurable": {"thread_id": run.id}}

        try:
            async for mode, chunk in self._graph.astream(
                initial_state(run.id, run.raw_briefing),
                config,
                stream_mode=["updates", "custom"],
            ):
                await self._events.publish(
                    SquadEvent(
                        run_id=run.id,
                        type=f"graph_{mode}",
                        payload=_serializable(chunk),
                    )
                )
            await self._finish(run, RunStatus.COMPLETED)

        except BudgetExceeded as exc:
            # Orçamento estourado não é falha: é pausa esperando decisão humana.
            logger.warning("run %s pausado por orçamento: %s", run.id, exc)
            await self._finish(run, RunStatus.AWAITING_HUMAN, awaiting_reason=str(exc))

        except DomainError as exc:
            logger.exception("run %s falhou por violação de contrato", run.id)
            await self._finish(run, RunStatus.FAILED, failure_reason=str(exc))

        except Exception as exc:
            logger.exception("run %s falhou", run.id)
            await self._finish(run, RunStatus.FAILED, failure_reason=repr(exc))

    async def _finish(self, run: Run, status: RunStatus, **extra: object) -> None:
        # Recarrega antes de gravar: `run` é o objeto de quando o run começou, e
        # gravar a partir dele apagaria o que foi escrito no meio do caminho
        # (`started_at`, extensões de orçamento aprovadas). Perder `started_at`
        # é perder a duração do run na trilha de auditoria.
        current = await self._runs.get(run.id) or run
        updated = current.with_status(status, finished_at=self._clock.now(), **extra)
        await self._runs.save(updated)
        await self._events.publish(
            SquadEvent(
                run_id=run.id,
                type="run_status",
                payload={"status": status.value, **{k: str(v) for k, v in extra.items()}},
            )
        )


class RetryRunUseCase:
    """Retoma um run que FALHOU, do último nó concluído.

    Diferença em relação ao `ResumeRunUseCase`
    ------------------------------------------
    - `Resume` responde a um `interrupt()`: o grafo pausou de propósito
      esperando decisão humana, e a decisão entra como retorno do interrupt.
    - `Retry` (aqui) recupera de uma **falha**: estouro de `max_tokens`, rate
      limit, queda de rede. Não há decisão a injetar — o grafo simplesmente
      continua do último checkpoint.

    O mecanismo é o `astream(None, config)`: entrada `None` diz ao LangGraph
    "não comece do início, retome deste thread". Story já aceita não é refeita,
    código já escrito não é regerado, token já gasto não é gasto de novo.

    Pré-requisito que morde
    -----------------------
    Isto depende do checkpointer ter o estado. Com `SQUAD_PERSISTENCE=memory` o
    saver é o `MemorySaver`: o estado vive **no processo**, então reiniciar o
    uvicorn (ou um `--reload` disparado por edição de arquivo) apaga tudo e não
    há o que retomar. Para retomada real entre reinícios, use
    `SQUAD_PERSISTENCE=mongo`.

    `has_checkpoint()` existe para dizer isso ao usuário ANTES de ele achar que
    perdeu o trabalho.
    """

    def __init__(
        self,
        runs: RunRepository,
        events: EventBusPort,
        clock: ClockPort,
        graph: Any,
    ) -> None:
        self._runs = runs
        self._events = events
        self._clock = clock
        self._graph = graph
        self._tasks: set[asyncio.Task[None]] = set()

    async def has_checkpoint(self, run_id: str) -> bool:
        """Existe estado salvo para retomar este run?"""
        run = await self._runs.get(run_id)
        if run is None or run.status is not RunStatus.FAILED:
            return False

        config = {"configurable": {"thread_id": run_id}}
        try:
            snapshot = await self._graph.aget_state(config)
        except Exception:
            return False
        return bool(snapshot and snapshot.values)

    async def execute(self, run_id: str) -> Run:
        run = await self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        if run.status is not RunStatus.FAILED:
            raise RunNotRetryable(run_id, run.status.value)

        if not await self.has_checkpoint(run_id):
            raise NoCheckpointAvailable(run_id)

        updated = run.with_status(RunStatus.RUNNING, failure_reason=None)
        await self._runs.save(updated)

        task = asyncio.create_task(self._retry(run_id), name=f"squad-retry:{run_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return updated

    async def _retry(self, run_id: str) -> None:
        config = {"configurable": {"thread_id": run_id}}
        try:
            # `None` como entrada = retoma do checkpoint. Passar o estado inicial
            # aqui recomeçaria do zero, que é exatamente o que queremos evitar.
            async for mode, chunk in self._graph.astream(
                None, config, stream_mode=["updates", "custom"]
            ):
                await self._events.publish(
                    SquadEvent(run_id=run_id, type=f"graph_{mode}", payload=_serializable(chunk))
                )
            await self._settle(run_id, RunStatus.COMPLETED)
        except DomainError as exc:
            logger.warning("retomada do run %s falhou de novo: %s", run_id, exc)
            await self._settle(run_id, RunStatus.FAILED, failure_reason=str(exc))
        except Exception as exc:
            logger.exception("retomada do run %s falhou", run_id)
            await self._settle(run_id, RunStatus.FAILED, failure_reason=repr(exc))

    async def _settle(self, run_id: str, status: RunStatus, **extra: object) -> None:
        run = await self._runs.get(run_id)
        if run is not None:
            await self._runs.save(run.with_status(status, finished_at=self._clock.now(), **extra))
        await self._events.publish(
            SquadEvent(run_id=run_id, type="run_status", payload={"status": status.value})
        )


class ResumeRunUseCase:
    """Retoma um run pausado em `interrupt()` com a decisão do humano.

    É o que torna o checkpointer útil na prática (§4.3): a decisão entra como
    retorno do `interrupt()` e o grafo continua do nó onde parou — não do zero.
    """

    def __init__(
        self,
        runs: RunRepository,
        events: EventBusPort,
        clock: ClockPort,
        graph: Any,
    ) -> None:
        self._runs = runs
        self._events = events
        self._clock = clock
        self._graph = graph
        self._tasks: set[asyncio.Task[None]] = set()

    async def execute(self, run_id: str, resolution: str) -> Run:
        run = await self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)

        updated = run.with_status(RunStatus.RUNNING, awaiting_reason=None)
        await self._runs.save(updated)

        task = asyncio.create_task(self._resume(run_id, resolution), name=f"squad-resume:{run_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return updated

    async def _resume(self, run_id: str, resolution: str) -> None:
        from langgraph.types import Command

        config = {"configurable": {"thread_id": run_id}}
        try:
            async for mode, chunk in self._graph.astream(
                Command(resume={"resolution": resolution}),
                config,
                stream_mode=["updates", "custom"],
            ):
                await self._events.publish(
                    SquadEvent(run_id=run_id, type=f"graph_{mode}", payload=_serializable(chunk))
                )
            run = await self._runs.get(run_id)
            if run is not None:
                await self._runs.save(
                    run.with_status(RunStatus.COMPLETED, finished_at=self._clock.now())
                )
        except Exception as exc:
            logger.exception("retomada do run %s falhou", run_id)
            run = await self._runs.get(run_id)
            if run is not None:
                await self._runs.save(run.with_status(RunStatus.FAILED, failure_reason=repr(exc)))


class ApproveBudgetUseCase:
    """Estende o orçamento de um run — decisão humana, registrada."""

    def __init__(self, runs: RunRepository, meter: TokenMeterPort) -> None:
        self._runs = runs
        self._meter = meter

    async def execute(self, run_id: str, extra_tokens: int) -> dict[str, Any]:
        run = await self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)

        snapshot = await self._meter.approve_extension(run_id, extra_tokens)
        await self._runs.save(run.model_copy(update={"budget": snapshot}))
        return snapshot.model_dump(mode="json")


def _serializable(chunk: Any) -> dict[str, Any]:
    """O stream do LangGraph traz tuplas e objetos; o SSE precisa de JSON."""
    if isinstance(chunk, dict):
        return chunk
    return {"value": repr(chunk)}
