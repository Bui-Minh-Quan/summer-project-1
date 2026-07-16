""" 
Abstract connector interface.

Every data source connector must inherit from BaseConnector
"""

from abc import ABC, abstractmethod
from datetime import datetime 

from models.document import Document, RawDocument

class BaseConnector(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return unique source identifier (e.g., 'fireant', 'vnexpress')"""
        pass
    
    @abstractmethod
    def fetch_latest_news(self, limit: int = 50) -> list[RawDocument]:
        # Fetch the latest financial news
        raise NotImplementedError
    
    @abstractmethod
    def fetch_latest_posts(self, limit: int = 50) -> list[RawDocument]:
        # Fetch the latest social posts 
        raise NotImplementedError 

    @abstractmethod
    def fetch_history(self, start_date: datetime, end_date: datetime) -> list[RawDocument]:
        # Fetch historical documents between two dates
        raise NotImplementedError
    
    @abstractmethod
    def health_check(self) -> bool:
        # Vertify whether the connector can communicate
        raise NotImplementedError
