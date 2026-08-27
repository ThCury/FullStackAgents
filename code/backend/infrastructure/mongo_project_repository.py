from __future__ import annotations

from pymongo import MongoClient

from infrastructure.mongo_repository import _to_api, _to_mongo


class MongoProjectRepository:
    def __init__(self, uri: str, database: str) -> None:
        self._client = MongoClient(uri, tz_aware=True)
        self._collection = self._client[database]["projects"]
        self._collection.create_index([("status", 1), ("timestamp", -1)])
        self._collection.create_index([("brasil_datetime", -1)])

    def create(self, document: dict) -> None:
        self._collection.insert_one(_to_mongo(document))

    def get(self, project_id: str) -> dict | None:
        document = self._collection.find_one({"_id": project_id})
        return _to_api(document) if document else None

    def list_projects(self) -> list[dict]:
        documents = self._collection.find({}).sort("timestamp", -1)
        return [_to_api(document) for document in documents]

    def append_message(self, project_id: str, message: dict) -> None:
        self._collection.update_one(
            {"_id": project_id}, {"$push": {"messages": _to_mongo(message)}}
        )

    def set_workspace(self, project_id: str, workspace: dict) -> None:
        self._collection.update_one(
            {"_id": project_id}, {"$set": {"workspace": _to_mongo(workspace)}}
        )

    def update_context(self, project_id: str, context: dict) -> None:
        self._collection.update_one(
            {"_id": project_id}, {"$set": {"context": _to_mongo(context)}}
        )

    def set_last_run(self, project_id: str, run_id: str) -> None:
        self._collection.update_one(
            {"_id": project_id}, {"$set": {"context.last_run_id": run_id}}
        )
