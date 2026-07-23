"""  
Abstract repository interface
"""

from abc import ABC, abstractmethod

from models.document import Document


class BaseRepository(ABC):
    # Abstract repository interface

    @abstractmethod
    def save(self, document: Document) -> str:
        # Insert a new document
        # returns: Document ID

        raise NotImplementedError
    
    @abstractmethod
    def save_many(self, documents: list[Document]) -> int:
        # Intert multiple documents
        # Return: Number of inserted documents
        raise NotImplementedError
    
    @abstractmethod
    def upsert(self, document: Document) -> str:
        # Insert or replace an existing document 
        # returns: DocumentID 
        raise NotImplementedError
    
    @abstractmethod
    def find_by_id(self, document_id: str) -> Document | None:
        # Find one document by ID 
        raise NotImplementedError
    
    def exists(self, document_id: str) -> bool:
        # Check wheather a document exists
        raise NotImplementedError
    
    @abstractmethod
    def count(self) -> int:
        # Return total number of stored documents
        raise NotImplementedError