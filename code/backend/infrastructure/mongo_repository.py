from __future__ import annotations

from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128
from pymongo import MongoClient, ReturnDocument

from domain.models.audit_time import now_audit_time
from domain.models.product_backlog import ProductBacklog
from domain.models.run_status import RunStatus


def _to_mongo(value: Any) -> Any:
    if isinstance(value, Decimal):
        return Decimal128(value)
    if isinstance(value, dict):
        return {key: _to_mongo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_mongo(item) for item in value]
    return value


def _to_api(value: Any) -> Any:
    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, dict):
        return {key: _to_api(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_api(item) for item in value]
    return value


class MongoRunRepository:
    def __init__(self, uri: str, database: str) -> None:
        self._client = MongoClient(uri, tz_aware=True)
        self._collection = self._client[database]["runs"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("status", 1), ("timestamp", -1)])
        self._collection.create_index([("requested_by.id", 1), ("timestamp", -1)])
        self._collection.create_index([("brasil_datetime", -1)])

    def create(self, document: dict) -> None:
        self._collection.insert_one(_to_mongo(document))

    def get(self, run_id: str) -> dict | None:
        document = self._collection.find_one({"_id": run_id})
        return _to_api(document) if document else None

    def mark_running(self, run_id: str) -> None:
        self._collection.update_one({"_id": run_id}, {"$set": {"status": RunStatus.RUNNING.value}})

    def reserve_sequence(self, run_id: str) -> int:
        document = self._collection.find_one_and_update(
            {"_id": run_id},
            {"$inc": {"audit.next_sequence": 1}},
            return_document=ReturnDocument.AFTER,
            projection={"audit.next_sequence": 1},
        )
        if document is None:
            raise KeyError(f"Run não encontrado: {run_id}")
        return document["audit"]["next_sequence"]

    def append_timeline(self, run_id: str, item: dict) -> None:
        self._collection.update_one({"_id": run_id}, {"$push": {"audit.timeline": _to_mongo(item)}})

    def update_streaming_response(self, run_id: str, call_id: str, content: str) -> None:
        result = self._collection.update_one(
            {"_id": run_id},
            {"$set": {"audit.timeline.$[call].response.content": content}},
            array_filters=[{"call.call_id": call_id}],
        )
        if result.matched_count == 0:
            raise KeyError(f"Run não encontrado: {run_id}")

    def finish_call(self, run_id: str, call_id: str, fields: dict) -> None:
        updates = {
            f"audit.timeline.$[call].{key}": _to_mongo(value) for key, value in fields.items()
        }
        self._collection.update_one(
            {"_id": run_id},
            {"$set": updates},
            array_filters=[{"call.call_id": call_id}],
        )

    def finish_run(self, run_id: str, output: ProductBacklog, totals: dict) -> None:
        self._collection.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "output": _to_mongo(output.model_dump()),
                    "audit.totals": _to_mongo(totals),
                    "status": RunStatus.COMPLETED.value,
                    "finished_at": _to_mongo(now_audit_time().model_dump()),
                }
            },
        )

    def fail_run(self, run_id: str, error: str) -> None:
        self._collection.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": RunStatus.FAILED.value,
                    "error": error,
                    "finished_at": _to_mongo(now_audit_time().model_dump()),
                }
            },
        )
