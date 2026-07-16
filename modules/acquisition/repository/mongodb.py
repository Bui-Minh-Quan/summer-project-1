""" 
MongoDB implementation of the repository
"""

from typing import Optional

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from models.document import Document
from base import BaseRepository

class MongoRepository(BaseRepository):
    # MongoDB repository for Document objects

    def __init__(self, uri: str, database: str = "financial_ai", collection: str = "raw_documents"):
        self.client = MongoClient(uri)

        self.db = self.client[database]
        
        self.collection: Collection = self.db[collection]

        # Make document id unique
        self.collection.create_index("id", unique=True)

    
    # CRUD
    def save(self, document: Document) -> str:
        # Insert a new document
        self.collection.insert_one(
            document.model_dump(mode="json")
        )

    def save_many(self, documents: list[Document]) -> int:
        # Insert many documents
        # Documents already existing will be ignored

        if not documents:
            return 0
        
        operations = []

        for document in documents:
            operations.append(
                UpdateOne(
                    {"id": document.id},
                    {"$setOnInsert": document.model_dump(mode="json")},
                    upsert=True
                )
            )
        
        result = self.collection.bulk_write(
            operations,
            ordered=False
        )

        return result.upserted_count
    
    def upsert(self, document: Document) -> str:
        # Replace document if it exists
        # Else just insert it
        self.collection.update_one(
            {"id": document.id},
            {"$set": document.model_dump(mode="json")},
            upsert=True
        )

        return document.id
    
    def find_by_id(self, document_id: str) -> Optional[Document]:
        result = self.collection.find_one({"id": document_id})

        if result is None:
            return None 
        
        result.pop("_id", None)

        return Document.model_validate(result) 
    
    def exists(self, document_id: str) -> bool:
        return (
            self.collection.count_documents({"id": document_id}, limit=1) > 0
        )
    
    def count(self) -> int:
        return self.collection.count_documents({})
    

    # Utility
    def delete(self, document_id: str) -> bool:
        result = self.collection.delete_one({"id": document_id})

        return result.deleted_count > 0
    
    def clear(self):
        self.collection.delete_many({})

    def close(self):
        self.client.close()
        