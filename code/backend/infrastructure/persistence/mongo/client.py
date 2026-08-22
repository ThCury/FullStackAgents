"""Conexão única com o squad_db - reaproveitada pelo checkpointer do
LangGraph e por todos os repositórios (mesmo Mongo, ADR-01)."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .... import config


_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(config.MONGODB_URI)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[config.MONGODB_DB]


async def ensure_indexes() -> None:
    db = get_database()
    await db["runs"].create_index("status")
    await db["runs"].create_index("created_at")

    await db["agent_messages"].create_index([("run_id", 1), ("seq", 1)], unique=True)
    await db["agent_messages"].create_index([("run_id", 1), ("from_agent", 1)])
    await db["agent_messages"].create_index("ref")

    await db["stories"].create_index([("run_id", 1), ("priority", 1)])
    await db["stories"].create_index("scenario_tag")

    await db["adrs"].create_index([("run_id", 1), ("story_ref", 1)])
    await db["test_reports"].create_index([("run_id", 1), ("story_ref", 1)])

    await db["token_ledger"].create_index([("run_id", 1), ("agent", 1)])

    await db["artifacts"].create_index([("run_id", 1), ("story_id", 1)])
