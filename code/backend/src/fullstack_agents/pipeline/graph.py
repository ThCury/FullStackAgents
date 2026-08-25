from __future__ import annotations

from time import monotonic
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from fullstack_agents.agents.product_owner.agent import ProductOwnerAgent
from fullstack_agents.application.costs import CostCalculator
from fullstack_agents.domain.models import now_audit_time
from fullstack_agents.domain.ports import RunRepository


class GraphState(TypedDict, total=False):
    run_id: str
    user_prompt: str
    raw_response: str
    output: dict


class ProductOwnerGraph:
    def __init__(
        self,
        repository: RunRepository,
        agent: ProductOwnerAgent,
        cost_calculator: CostCalculator,
        stream_persist_interval_ms: int,
    ) -> None:
        self._repository = repository
        self._agent = agent
        self._cost_calculator = cost_calculator
        self._stream_persist_interval_seconds = stream_persist_interval_ms / 1000
        builder = StateGraph(GraphState)
        builder.add_node("plan", self._plan)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", END)
        self._compiled = builder.compile()

    def invoke(self, state: GraphState) -> GraphState:
        return self._compiled.invoke(state)

    def _plan(self, state: GraphState) -> GraphState:
        run_id = state["run_id"]
        call_id = f"call_{uuid4().hex}"
        request = self._agent.build_request(state["user_prompt"])
        started_at = now_audit_time()
        call = {
            "sequence": self._repository.reserve_sequence(run_id),
            "type": "LLM_CALL",
            "call_id": call_id,
            "attempt": 1,
            "agent": {"id": "po", "role": self._agent.role, "version": self._agent.version},
            "request": {
                "from": {"type": "agent", "id": "po", "role": self._agent.role},
                "to": {"type": "llm_provider", "id": self._agent.provider},
                "prompt": request.prompt,
                "system_prompt": request.system_prompt,
                "system_prompt_version": "po-v1",
                "model": request.model,
                "provider": self._agent.provider,
                "parameters": {"temperature": request.temperature},
                "effort": request.effort,
            },
            "response": {"from": {"type": "llm_provider", "id": self._agent.provider}, "to": {"type": "agent", "id": "po"}, "content": ""},
            "usage": {"input_tokens": None, "output_tokens": None, "cached_tokens": None, "total_tokens": None},
            "cost": {"estimated": None, "billed": None},
            "started_at": started_at.model_dump(),
            "status": "STREAMING",
            "error": None,
            **started_at.model_dump(),
        }
        self._repository.append_timeline(run_id, call)
        self._append_flow_event(run_id, "LLM_CALL_STARTED", "Chamada do PO ao modelo iniciada.", None)

        content = ""
        last_persist = monotonic()

        def on_delta(delta: str) -> None:
            nonlocal content, last_persist
            content += delta
            if monotonic() - last_persist >= self._stream_persist_interval_seconds:
                self._repository.update_streaming_response(run_id, call_id, content)
                last_persist = monotonic()

        before = monotonic()
        try:
            backlog, raw_response, completion = self._agent.run(state["user_prompt"], on_delta)
        except Exception as error:
            failed_at = now_audit_time()
            self._repository.finish_call(
                run_id,
                call_id,
                {
                    "response.content": content,
                    "finished_at": failed_at.model_dump(),
                    "latency_ms": round((monotonic() - before) * 1000),
                    "status": "FAILED",
                    "error": str(error),
                },
            )
            self._append_flow_event(run_id, "LLM_CALL_FAILED", "Chamada do modelo falhou.", False)
            raise
        latency_ms = round((monotonic() - before) * 1000)
        completed_at = now_audit_time()
        totals = self._cost_calculator.totals(
            completion.get("input_tokens"),
            completion.get("output_tokens"),
            completion.get("cached_tokens"),
            latency_ms,
        )
        self._repository.finish_call(
            run_id,
            call_id,
            {
                "response.content": raw_response,
                "response.finish_reason": completion.get("finish_reason"),
                "provider_response_id": completion.get("provider_response_id"),
                "usage": {
                    "input_tokens": completion.get("input_tokens"),
                    "output_tokens": completion.get("output_tokens"),
                    "cached_tokens": completion.get("cached_tokens"),
                    "total_tokens": totals.total_tokens,
                },
                "cost": {"estimated": totals.estimated_cost.model_dump(), "billed": None},
                "finished_at": completed_at.model_dump(),
                "latency_ms": latency_ms,
                "status": "SUCCEEDED",
            },
        )
        self._append_flow_event(run_id, "LLM_CALL_SUCCEEDED", "Resposta do modelo recebida e persistida.", None)
        self._repository.finish_run(run_id, backlog, totals.model_dump())
        self._append_flow_event(
            run_id,
            "AGENT_RESULT_ACCEPTED",
            "Resultado do PO validado: requisitos e histórias de usuário disponíveis.",
            True,
        )
        self._append_flow_event(run_id, "RUN_COMPLETED", "Fluxo do Product Owner concluído.", True)
        return {"raw_response": raw_response, "output": backlog.model_dump()}

    def _append_flow_event(self, run_id: str, event: str, summary: str, approved: bool | None) -> None:
        time = now_audit_time()
        self._repository.append_timeline(
            run_id,
            {
                "sequence": self._repository.reserve_sequence(run_id),
                "type": "FLOW_EVENT",
                "event": event,
                "from": {"type": "orchestrator", "id": "product_owner_graph"},
                "to": {"type": "agent", "id": "po", "role": "PRODUCT_OWNER"},
                "attempt": 1,
                "approved": approved,
                "summary": summary,
                **time.model_dump(),
            },
        )
