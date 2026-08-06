"""
MongoDB implementation of the generic repository.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from modules.acquisition.repository.base import BaseRepository

T = TypeVar("T", bound=BaseModel)


class MongoRepository(BaseRepository[T], Generic[T]):
    """MongoDB generic repository for Pydantic models."""

    def __init__(
        self,
        uri: str,
        database: str = "financial_ai",
        collection: str = "raw_documents",
        model_class: type[T] | None = None,
    ) -> None:
        self.client: MongoClient[dict[str, Any]] = MongoClient(uri)
        self.db: Database[dict[str, Any]] = self.client[database]
        self.collection: Collection[dict[str, Any]] = self.db[collection]
        self.model_class = model_class

        # Ensure index on canonical 'id' and 'fingerprint'
        self.collection.create_index("id", unique=True)
        self.collection.create_index("fingerprint", unique=True, sparse=True)

    def save(self, entity: T) -> str:
        """Insert a single entity."""
        self.collection.insert_one(entity.model_dump(mode="json"))
        entity_id = getattr(entity, "id", None)
        return str(entity_id) if entity_id else ""

    def save_many(self, entities: list[T]) -> int:
        """
        Insert multiple entities using unordered bulk writes.
        Silently ignores duplicate key errors (code 11000).
        """
        if not entities:
            return 0

        operations = []
        for entity in entities:
            entity_id = getattr(entity, "id", None)
            operations.append(
                UpdateOne(
                    {"id": entity_id},
                    {"$setOnInsert": entity.model_dump(mode="json")},
                    upsert=True,
                )
            )

        try:
            result = self.collection.bulk_write(operations, ordered=False)
            return result.upserted_count
        except BulkWriteError as bwe:
            real_errors = [
                err
                for err in bwe.details.get("writeErrors", [])
                if err.get("code") != 11000
            ]
            if real_errors:
                raise

            successful_saves = bwe.details.get("nUpserted", 0) + bwe.details.get(
                "nInserted", 0
            )
            return successful_saves

    def upsert(self, entity: T) -> str:
        """Insert or replace an existing entity."""
        entity_id = getattr(entity, "id", None)
        self.collection.update_one(
            {"id": entity_id},
            {"$set": entity.model_dump(mode="json")},
            upsert=True,
        )
        return str(entity_id) if entity_id else ""

    def find_by_id(self, entity_id: str) -> T | None:
        result = self.collection.find_one({"id": entity_id})
        if result is None:
            return None

        result.pop("_id", None)
        assert self.model_class is not None
        return self.model_class.model_validate(result)

    def exists(self, entity_id: str) -> bool:
        return self.collection.count_documents({"id": entity_id}, limit=1) > 0

    def count(self) -> int:
        return self.collection.count_documents({})

    def delete(self, entity_id: str) -> bool:
        result = self.collection.delete_one({"id": entity_id})
        return result.deleted_count > 0

    def clear(self) -> None:
        self.collection.delete_many({})

    def close(self) -> None:
        self.client.close()

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return (
            self.collection.count_documents({"fingerprint": fingerprint}, limit=1) > 0
        )

    def get_latest_timestamp(
        self, source: str | None = None, doc_type: str | None = None
    ) -> datetime | None:
        query: dict[str, Any] = {}
        if source:
            query["source"] = source
        if doc_type:
            query["document_type"] = doc_type

        doc = self.collection.find_one(query, sort=[("published_at", -1)])
        if doc and "published_at" in doc:
            return doc["published_at"]
        return None
