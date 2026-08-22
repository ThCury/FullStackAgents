"""Checkpointer do LangGraph, no mesmo squad_db usado pelos repositórios
(ADR-01/03) - é o que permite retomar um run do último nó em vez do zero se
o processo cair no meio de uma demo, e é o mecanismo por trás do `interrupt()`
em escalate (§4.3).

Nota de correção sobre a arquitetura: o documento cita
`from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver`. Verificado
em runtime que essa classe/submódulo não existe mais em
langgraph-checkpoint-mongodb==0.4.0 - a lib unificou o saver em uma única
`MongoDBSaver` (expõe get/put síncronos e aget/aput assíncronos na mesma
classe). O construtor dela exige um cliente **pymongo síncrono**
(`pymongo.MongoClient`), não o Motor `AsyncIOMotorClient` usado pelos
repositórios - por isso o checkpointer usa seu próprio client, mesmo
apontando para o mesmo servidor/banco Mongo."""
from __future__ import annotations

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from .. import config

_checkpointer_client: MongoClient | None = None


def build_checkpointer() -> MongoDBSaver:
    global _checkpointer_client
    if _checkpointer_client is None:
        _checkpointer_client = MongoClient(config.MONGODB_URI)
    return MongoDBSaver(_checkpointer_client, db_name=config.MONGODB_DB)


def close_checkpointer() -> None:
    global _checkpointer_client
    if _checkpointer_client is not None:
        _checkpointer_client.close()
        _checkpointer_client = None
