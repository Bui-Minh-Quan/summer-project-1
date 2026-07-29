"""
Abstract generic repository interface for Pydantic domain models.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(ABC, Generic[T]):
    """Abstract repository contract operating on any Pydantic model."""

    @abstractmethod
    def save(self, entity: T) -> str:
        """Insert a single entity and return its primary identifier."""
        raise NotImplementedError

    @abstractmethod
    def save_many(self, entities: list[T]) -> int:
        """Insert multiple entities and return the count of successfully stored records."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, entity: T) -> str:
        """Insert or replace an existing entity by its ID."""
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, entity_id: str) -> T | None:
        """Find one entity by its string ID."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check whether an entity exists by ID."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return total count of stored records."""
        raise NotImplementedError