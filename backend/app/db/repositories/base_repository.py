"""
Base Repository

Provides common patterns and utilities for all MongoDB repositories.
"""

from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.logging import logger
from app.utils.timezone import beijing_time_now


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize repository with database connection.

        Args:
            db: MongoDB database instance
        """
        self.db = db

    async def _find_one(
        self, collection: str, query: Dict[str, Any], projection: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single document in a collection.

        Args:
            collection: Collection name
            query: Query filter
            projection: Optional projection to limit returned fields

        Returns:
            Found document or None
        """
        try:
            if projection:
                return await self.db[collection].find_one(query, projection=projection)
            return await self.db[collection].find_one(query)
        except Exception as e:
            logger.error(f"Error finding document in {collection}: {str(e)}")
            raise

    async def _find_many(
        self,
        collection: str,
        query: Dict[str, Any],
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents in a collection.

        Args:
            collection: Collection name
            query: Query filter
            sort: Optional sort specification [(field, direction), ...]
            limit: Optional limit on number of results

        Returns:
            List of found documents
        """
        try:
            cursor = self.db[collection].find(query)
            if sort:
                cursor = cursor.sort(sort)
            return await cursor.to_list(length=self._paginate(limit, max_limit=1000))
        except Exception as e:
            logger.error(f"Error finding documents in {collection}: {str(e)}")
            raise

    async def _insert_one(
        self, collection: str, document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Insert a single document into a collection.

        Args:
            collection: Collection name
            document: Document to insert

        Returns:
            Status dictionary
        """
        try:
            await self.db[collection].insert_one(document)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error inserting document in {collection}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _update_one(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        array_filters: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Update a single document in a collection.

        Args:
            collection: Collection name
            query: Query filter
            update: Update operations
            array_filters: Optional array filters for update operations

        Returns:
            Status dictionary
        """
        try:
            if array_filters:
                result = await self.db[collection].update_one(
                    query, update, array_filters=array_filters
                )
            else:
                result = await self.db[collection].update_one(query, update)

            if result.modified_count > 0:
                return {"status": "success"}
            return {"status": "failed", "message": "No documents modified"}
        except Exception as e:
            logger.error(f"Error updating document in {collection}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _delete_one(
        self, collection: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delete a single document from a collection.

        Args:
            collection: Collection name
            query: Query filter

        Returns:
            Status dictionary
        """
        try:
            result = await self.db[collection].delete_one(query)
            if result.deleted_count > 0:
                return {"status": "success", "deleted_count": result.deleted_count}
            return {"status": "failed", "message": "No documents deleted"}
        except Exception as e:
            logger.error(f"Error deleting document in {collection}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _delete_many(
        self, collection: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delete multiple documents from a collection.

        Args:
            collection: Collection name
            query: Query filter

        Returns:
            Status dictionary
        """
        try:
            result = await self.db[collection].delete_many(query)
            return {
                "status": "success",
                "deleted_count": result.deleted_count,
            }
        except Exception as e:
            logger.error(f"Error deleting documents in {collection}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _get_timestamp(self) -> Any:
        """Get current timestamp in Beijing timezone."""
        return beijing_time_now()

    def _paginate(self, limit: Optional[int] = None, max_limit: int = 1000) -> int:
        """
        Apply safe pagination limits to prevent unbounded queries.

        Args:
            limit: Requested limit (None = unbounded)
            max_limit: Maximum allowed limit for this query type

        Returns:
            Safe limit value
        """
        if limit is None:
            logger.warning("Unbounded query detected - applying max_limit")
            return max_limit
        if limit > max_limit:
            logger.warning(f"Limit {limit} exceeds max_limit {max_limit} - capping")
            return max_limit
        return limit
