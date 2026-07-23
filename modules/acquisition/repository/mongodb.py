""" 
MongoDB implementation of the repository
"""

from typing import Optional, Any

from datetime import datetime

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError
from pymongo.database import Database

from models.document import Document
from repository.base import BaseRepository

class MongoRepository(BaseRepository):
    # MongoDB repository for Document objects

    def __init__(self, uri: str, database: str = "financial_ai", collection: str = "raw_documents") -> None:
        self.client: MongoClient[dict[str, Any]] = MongoClient(uri)
        self.db: Database[dict[str, Any]] = self.client[database]
        self.collection: Collection[dict[str, Any]] = self.db[collection]

        # Make document id unique
        self.collection.create_index("id", unique=True)

        self.collection.create_index("fingerprint", unique=True, sparse=True)


    
    # CRUD
    def save(self, document: Document) -> str:
        # Insert a new document
        self.collection.insert_one(
            document.model_dump(mode="json")
        )

        return document.id

    def save_many(self, documents: list[Document]) -> int:
        """
        Insert many documents using unordered bulk writes.
        Silently ignores any duplicate ID or duplicate fingerprint errors.
        """
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
        
        try:
            result = self.collection.bulk_write(operations, ordered=False)
            return result.upserted_count
            
        except BulkWriteError as bwe:
            # Check if there are any errors OTHER than code 11000 (Duplicate Key)
            real_errors = [
                err for err in bwe.details.get("writeErrors", [])
                if err.get("code") != 11000
            ]
            
            if real_errors:
                # If a real database failure occurred (e.g., auth failure, disk full), crash loudly!
                raise bwe
            
            # If all errors were just duplicate keys, gracefully extract the count of successful saves!
            successful_saves = bwe.details.get("nUpserted", 0) + bwe.details.get("nInserted", 0)
            return successful_saves
        
        
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
    
    # Helper 
    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return self.collection.count_documents({"fingerprint": fingerprint}, limit=1) > 0
    

    def get_latest_timestamp(self, source: Optional[str] = None, doc_type: Optional[str] = None) -> Optional[datetime]:
        query = {}
        if source:
            query["source"] = source 
        if doc_type:
            query["document_type"] = doc_type
        
        doc = self.collection.find_one(query, sort=[("published_at", -1)])

        if doc and "published_at" in doc:
            return doc["published_at"]
        return None

        