"""
Abstract generic repository interface for Pydantic models.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

# T can represent Document, MarketQuote, ExtractionResult, etc.
T = TypeVar("T", bound=BaseModel)


class BaseRepository(ABC, Generic[T]):
    """Abstract repository interface operating on any Pydantic model."""

    @abstractmethod
    def save(self, entity: T) -> str:
        """Insert a new entity and return its string ID."""
        raise NotImplementedError

    @abstractmethod
    def save_many(self, entities: list[T]) -> int:
        """Insert multiple entities and return the count of stored records."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, entity: T) -> str:
        """Insert or update an existing entity by ID."""
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, entity_id: str) -> T | None:
        """Find one entity by its unique ID."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check whether an entity exists by ID."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return total number of stored entities in the collection."""
        raise NotImplementedError
