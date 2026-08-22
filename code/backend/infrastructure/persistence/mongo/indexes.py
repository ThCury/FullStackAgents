"""Índices do `squad_db` — §7.1 da arquitetura.

Chamado no startup da API. `create_index` é idempotente, então rodar sempre é
seguro e evita o clássico "funciona na minha máquina porque eu criei o índice na
mão".

Cada índice aqui corresponde a uma consulta real do Console. Índice sem consulta
é custo de escrita sem benefício — se remover uma tela, remova o índice.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

# Motor é genérico sobre o tipo do documento. O alias evita repetir o
# parâmetro em cada assinatura e deixa óbvio que trafegamos dict cru.
type MongoDatabase = AsyncIOMotorDatabase[dict[str, Any]]


async def ensure_indexes(db: MongoDatabase) -> list[str]:
    """Cria os índices e devolve os nomes, para log de startup."""
    created: list[str] = []

    # Tela: lista de runs recentes no Launcher.
    created.append(await db.runs.create_index([("status", ASCENDING)]))
    created.append(await db.runs.create_index([("created_at", DESCENDING)]))

    # Tela: Timeline. É a consulta mais quente do Console — ordem total por run.
    created.append(
        await db.agent_messages.create_index([("run_id", ASCENDING), ("seq", ASCENDING)])
    )
    # Tela: filtro "só o que o Dev Agent disse".
    created.append(
        await db.agent_messages.create_index([("run_id", ASCENDING), ("from_agent", ASCENDING)])
    )
    # Tela: "todas as mensagens sobre esta story".
    created.append(await db.agent_messages.create_index([("ref", ASCENDING)]))

    # Tela: Inspector (prompt/resposta crus) e painel de cache hit.
    created.append(await db.llm_calls.create_index([("run_id", ASCENDING), ("agent", ASCENDING)]))

    # Tela: Backlog, ordenado por prioridade.
    created.append(await db.stories.create_index([("run_id", ASCENDING), ("priority", ASCENDING)]))
    created.append(await db.stories.create_index([("scenario_tag", ASCENDING)]))

    # Tela: histórico de tentativas de uma story (evolução após reprovação).
    created.append(
        await db.artifacts.create_index([("run_id", ASCENDING), ("story_ref", ASCENDING)])
    )
    created.append(
        await db.test_reports.create_index([("run_id", ASCENDING), ("story_ref", ASCENDING)])
    )

    # Tela: Decision Log.
    created.append(await db.adrs.create_index([("run_id", ASCENDING)]))

    return created
