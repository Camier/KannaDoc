from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict, List, Optional
from bson import ObjectId
from bson.errors import InvalidId


class BaseRepository:
    """Base repository with generic CRUD operations for MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection_name = self.__class__.__name__.lower().replace("repository", "")

    @property
    def collection(self):
        """Get the MongoDB collection for this repository."""
        return self.db[self.collection_name]

    async def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find a document by its ID."""
        try:
            return await self.collection.find_one({"_id": ObjectId(doc_id)})
        except InvalidId:
            # Handle string IDs
            return await self.collection.find_one({"_id": doc_id})

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query."""
        return await self.collection.find_one(query)

    async def find_many(
        self, query: Dict[str, Any] = None, sort: List[tuple] = None, limit: int = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents matching the query."""
        query = query or {}
        cursor = self.collection.find(query)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        return await cursor.to_list(length=limit or 1000)

    async def insert_one(self, data: Dict[str, Any]) -> str:
        """Insert a single document and return its ID."""
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> bool:
        """Update a single document. Returns True if modified."""
        result = await self.collection.update_one(
            query, {"$set": update}, upsert=upsert
        )
        return result.modified_count > 0 or (upsert and result.upserted_id)

    async def update_by_id(self, doc_id: str, update: Dict[str, Any]) -> bool:
        """Update a document by its ID."""
        try:
            obj_id = ObjectId(doc_id)
        except InvalidId:
            obj_id = doc_id
        return await self.update_one({"_id": obj_id}, update)

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete a single document. Returns True if deleted."""
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

    async def delete_by_id(self, doc_id: str) -> bool:
        """Delete a document by its ID."""
        try:
            obj_id = ObjectId(doc_id)
        except InvalidId:
            obj_id = doc_id
        return await self.delete_one({"_id": obj_id})

    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if a document exists matching the query."""
        return await self.collection.count_documents(query, limit=1) > 0

    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching the query."""
        query = query or {}
        return await self.collection.count_documents(query)
