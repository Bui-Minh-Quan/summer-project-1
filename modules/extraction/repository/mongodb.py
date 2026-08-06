"""
Generic MongoDB repository implementation supporting custom indexing and Pydantic hydration.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from modules.extraction.repository.base import BaseRepository

T = TypeVar("T", bound=BaseModel)


class MongoRepository(BaseRepository[T], Generic[T]):
    """MongoDB generic repository for any Pydantic schema."""

    def __init__(
        self,
        uri: str,
        database: str = "financial_ai",
        collection: str = "staged_graph_knowledge",
        model_class: type[T] | None = None,
        index_fields: list[str] | None = None,
    ) -> None:
        self.client: MongoClient[dict[str, Any]] = MongoClient(uri)
        self.db: Database[dict[str, Any]] = self.client[database]
        self.collection: Collection[dict[str, Any]] = self.db[collection]
        self.model_class = model_class

        # 1. Always enforce unique index on canonical 'id'
        self.collection.create_index("id", unique=True)

        # 2. Dynamically create additional indexes (e.g., ['document_id', 'entities.ticker'])
        if index_fields:
            for field in index_fields:
                self.collection.create_index(field)

    def save(self, entity: T) -> str:
        """Insert a single entity."""
        payload = entity.model_dump(mode="json")
        self.collection.insert_one(payload)
        entity_id = getattr(entity, "id", None)
        return str(entity_id) if entity_id else ""

    def save_many(self, entities: list[T]) -> int:
        """
        Insert multiple entities using unordered bulk writes.
        Silently bypasses duplicate key collisions (code 11000).
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
                err for err in bwe.details.get("writeErrors", [])
                if err.get("code") != 11000
            ]
            if real_errors:
                raise

            return bwe.details.get("nUpserted", 0) + bwe.details.get("nInserted", 0)

    def upsert(self, entity: T) -> str:
        """Insert or replace an entity by its primary ID."""
        entity_id = getattr(entity, "id", None)
        self.collection.update_one(
            {"id": entity_id},
            {"$set": entity.model_dump(mode="json")},
            upsert=True,
        )
        return str(entity_id) if entity_id else ""

    def find_by_id(self, entity_id: str) -> Any | None:
        """Find entity by ID and hydrate into model_class if configured."""
        result = self.collection.find_one({"id": entity_id})
        if result is None:
            return None

        result.pop("_id", None)
        if self.model_class is not None:
            return self.model_class.model_validate(result)

        return result  # Fallback to raw dict if no model_class was specified

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