"""
Abstract connector interface.

Every data source connector must inherit from BaseConnector and define its payload type.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

# T MUST be defined at the root module level (no indentation!)
T = TypeVar("T")


class BaseConnector(ABC, Generic[T]):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return unique source identifier (e.g., 'fireant', 'vnstock')."""

    @abstractmethod
    def fetch_latest(self, **kwargs: Any) -> list[T]:
        """Fetch the most recent data stream (intraday quotes, latest news, etc.)."""

    @abstractmethod
    def fetch_history(
        self, start_date: datetime, end_date: datetime, **kwargs: Any
    ) -> list[T]:
        """Fetch historical records bounded by two timestamps."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify whether the remote data source or API is reachable and operational."""
