"""
Abstract generic publisher interface for event-driven streaming.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BasePublisher(ABC, Generic[T]):
    """Abstract publisher interface for broadcasting Pydantic domain events."""

    @abstractmethod
    def publish(self, topic: str, entity: T, key: str | None = None) -> bool:
        """Publish a single entity to a specified topic/channel."""
        raise NotImplementedError

    @abstractmethod
    def publish_batch(self, topic: str, entities: list[T]) -> int:
        """Publish a batch of entities and return the count of successfully transmitted messages."""
        raise NotImplementedError

    @abstractmethod
    def flush(self, timeout: float = 10.0) -> int:
        """Flush pending network buffers without terminating the producer connection."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Terminate open network connections to the broker."""
        raise NotImplementedError