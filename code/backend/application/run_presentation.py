from __future__ import annotations

from typing import Literal

RunDataset = Literal["full", "resume"]


class RunPresentation:
    """Cria visões de leitura sem alterar o documento completo de auditoria."""

    @staticmethod
    def render(run: dict, dataset: RunDataset) -> dict:
        if dataset == "full":
            return run
        return RunPresentation._resume(run)

    @staticmethod
    def list_item(run: dict) -> dict:
        return {
            "run_id": run["_id"],
            "status": RunPresentation._public_status(run["status"]),
            "prompt_preview": RunPresentation._preview(run["input"]["content"]),
            "requested_by": {
                "id": run["requested_by"]["id"],
                "display_name": run["requested_by"]["display_name"],
            },
            "brasil_datetime": run["brasil_datetime"],
            "finished_brasil_datetime": RunPresentation._brasil_datetime(run.get("finished_at")),
        }

    @staticmethod
    def _resume(run: dict) -> dict:
        call = RunPresentation._latest_llm_call(run)
        totals = run["audit"]["totals"]
        return {
            "run_id": run["_id"],
            "flow": run["flow"],
            "status": RunPresentation._public_status(run["status"]),
            "execution_status": run["status"],
            "requested_by": run["requested_by"],
            "prompt_sent": run["input"]["content"],
            "response_received": run["output"],
            "tokens_spent": {
                "input": totals["input_tokens"],
                "output": totals["output_tokens"],
                "cached": totals["cached_tokens"],
                "total": totals["total_tokens"],
            },
            "time_spent": {
                "started_at": run["brasil_datetime"],
                "finished_at": RunPresentation._brasil_datetime(run.get("finished_at")),
                "duration_ms": RunPresentation._latency_ms(call),
            },
            "llm": RunPresentation._llm_metadata(call),
            "error": RunPresentation._short_error(run["error"]),
        }

    @staticmethod
    def _latest_llm_call(run: dict) -> dict | None:
        calls = (item for item in run["audit"]["timeline"] if item["type"] == "LLM_CALL")
        return next(reversed(list(calls)), None)

    @staticmethod
    def _public_status(status: str) -> str:
        return {
            "COMPLETED": "SUCCESS",
            "FAILED": "FAILED",
            "PENDING": "PENDING",
            "RUNNING": "PENDING",
        }[status]

    @staticmethod
    def _brasil_datetime(value: dict | None) -> str | None:
        return value["brasil_datetime"] if value else None

    @staticmethod
    def _latency_ms(call: dict | None) -> int | None:
        return call.get("latency_ms") if call else None

    @staticmethod
    def _llm_metadata(call: dict | None) -> dict | None:
        if call is None:
            return None
        request = call["request"]
        return {
            "agent": call["agent"],
            "provider": request["provider"],
            "model": request["model"],
            "system_prompt": request["system_prompt"],
            "effort": request["effort"],
        }

    @staticmethod
    def _short_error(error: str | None) -> str | None:
        if error is None or len(error) <= 500:
            return error
        return f"{error[:497]}..."

    @staticmethod
    def _preview(content: str, max_length: int = 160) -> str:
        normalized = " ".join(content.split())
        if len(normalized) <= max_length:
            return normalized
        return f"{normalized[: max_length - 3]}..."
