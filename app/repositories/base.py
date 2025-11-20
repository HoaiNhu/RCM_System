"""
Base Repository following Repository Pattern and Interface Segregation Principle
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from bson import ObjectId


class IRepository(ABC):
    """Interface for repository operations"""
    
    @abstractmethod
    def find_one(self, filter_dict: Dict[str, Any]) -> Optional[Dict]:
        """Find one document"""
        pass
    
    @abstractmethod
    def find_many(self, filter_dict: Dict[str, Any], limit: Optional[int] = None) -> List[Dict]:
        """Find multiple documents"""
        pass
    
    @abstractmethod
    def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert one document"""
        pass
    
    @abstractmethod
    def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any], upsert: bool = False) -> bool:
        """Update one document"""
        pass
    
    @abstractmethod
    def count(self, filter_dict: Dict[str, Any]) -> int:
        """Count documents"""
        pass


class BaseRepository(IRepository):
    """Base repository implementation with common MongoDB operations"""
    
    def __init__(self, db: Database, collection_name: str):
        self.db = db
        self.collection = db[collection_name]
    
    def find_one(self, filter_dict: Dict[str, Any]) -> Optional[Dict]:
        """Find one document by filter"""
        return self.collection.find_one(filter_dict)
    
    def find_many(self, filter_dict: Dict[str, Any], limit: Optional[int] = None, sort: Optional[List] = None) -> List[Dict]:
        """Find multiple documents"""
        query = self.collection.find(filter_dict)
        if sort:
            query = query.sort(sort)
        if limit:
            query = query.limit(limit)
        return list(query)
    
    def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert one document and return ID"""
        result = self.collection.insert_one(document)
        return str(result.inserted_id)
    
    def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any], upsert: bool = False) -> bool:
        """Update one document"""
        result = self.collection.update_one(filter_dict, update_dict, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)
    
    def count(self, filter_dict: Dict[str, Any]) -> int:
        """Count documents matching filter"""
        return self.collection.count_documents(filter_dict)
    
    def find_by_id(self, document_id: str) -> Optional[Dict]:
        """Find document by ObjectId"""
        try:
            return self.collection.find_one({'_id': ObjectId(document_id)})
        except:
            return None
