"""
Redis caching layer for frequently accessed data.
Caches model configurations, user data, and knowledge base metadata.
"""

import json
import logging
from typing import Optional, Any, List
from app.db.redis import redis
from app.core.logging import logger

# Default TTL values (in seconds)
DEFAULT_TTL = 3600  # 1 hour
MODEL_CONFIG_TTL = 1800  # 30 minutes
CONVERSATION_MODEL_CONFIG_TTL = 900  # 15 minutes
USER_DATA_TTL = 3600  # 1 hour
KB_METADATA_TTL = 1800  # 30 minutes
SEARCH_RESULTS_TTL = 600  # 10 minutes


class CacheService:
    """
    High-performance Redis caching service with async support.
    Provides caching for model configs, user data, KB metadata, and search results.
    """

    # Cache key prefixes
    PREFIX_MODEL_CONFIG = "model_config"
    PREFIX_CONV_MODEL_CONFIG = "conv_model_config"
    PREFIX_USER_DATA = "user"
    PREFIX_KB_METADATA = "kb"
    PREFIX_SEARCH_RESULTS = "search"

    @staticmethod
    def _make_key(prefix: str, identifier: str) -> str:
        """Generate standardized cache key."""
        return f"{prefix}:{identifier}"

    @staticmethod
    def _make_pattern(prefix: str, identifier: str = "*") -> str:
        """Generate standardized cache pattern for invalidation."""
        return f"{prefix}:{identifier}"

    async def get(self, key: str) -> Optional[dict]:
        """
        Retrieve cached data by key.

        Args:
            key: Cache key

        Returns:
            Cached dict or None if not found/expired
        """
        try:
            conn = await redis.get_redis_connection()
            cached = await conn.get(key)

            if cached:
                logger.debug(f"Cache hit: {key}")
                return json.loads(cached)

            logger.debug(f"Cache miss: {key}")
            return None

        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            # Fail gracefully - return None to trigger DB fetch
            return None

    async def set(self, key: str, value: dict, ttl: int = DEFAULT_TTL) -> bool:
        """
        Store data in cache with TTL.

        Args:
            key: Cache key
            value: Data to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = await redis.get_redis_connection()
            await conn.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            conn = await redis.get_redis_connection()
            keys = await conn.keys(pattern)

            if keys:
                await conn.delete(*keys)
                logger.info(
                    f"Invalidated {len(keys)} cache entries matching: {pattern}"
                )
                return len(keys)

            return 0

        except Exception as e:
            logger.warning(f"Cache invalidation failed for {pattern}: {e}")
            return 0

    async def delete(self, key: str) -> bool:
        """
        Delete specific cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if key existed and was deleted
        """
        try:
            conn = await redis.get_redis_connection()
            result = await conn.delete(key)
            return result > 0

        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            conn = await redis.get_redis_connection()
            return await conn.exists(key) > 0

        except Exception as e:
            logger.warning(f"Cache exists check failed for {key}: {e}")
            return False

    # Model Config caching
    async def get_model_config(self, username: str) -> Optional[dict]:
        """Get cached model configuration for user."""
        key = self._make_key(self.PREFIX_MODEL_CONFIG, username)
        return await self.get(key)

    async def set_model_config(self, username: str, config: dict) -> bool:
        """Cache model configuration for user."""
        key = self._make_key(self.PREFIX_MODEL_CONFIG, username)
        return await self.set(key, config, MODEL_CONFIG_TTL)

    async def invalidate_model_config(self, username: str) -> bool:
        """Invalidate cached model configuration for user."""
        key = self._make_key(self.PREFIX_MODEL_CONFIG, username)
        return await self.delete(key)

    async def get_conversation_model_config(
        self, conversation_id: str
    ) -> Optional[dict]:
        """Get cached model configuration for conversation."""
        key = self._make_key(self.PREFIX_CONV_MODEL_CONFIG, conversation_id)
        return await self.get(key)

    async def set_conversation_model_config(
        self, conversation_id: str, config: dict
    ) -> bool:
        """Cache model configuration for conversation."""
        key = self._make_key(self.PREFIX_CONV_MODEL_CONFIG, conversation_id)
        return await self.set(key, config, CONVERSATION_MODEL_CONFIG_TTL)

    async def invalidate_conversation_model_config(self, conversation_id: str) -> bool:
        """Invalidate cached model configuration for conversation."""
        key = self._make_key(self.PREFIX_CONV_MODEL_CONFIG, conversation_id)
        return await self.delete(key)

    # User data caching
    async def get_user_data(self, username: str) -> Optional[dict]:
        """Get cached user data."""
        key = self._make_key(self.PREFIX_USER_DATA, username)
        return await self.get(key)

    async def set_user_data(self, username: str, user_data: dict) -> bool:
        """Cache user data."""
        key = self._make_key(self.PREFIX_USER_DATA, username)
        return await self.set(key, user_data, USER_DATA_TTL)

    async def invalidate_user_data(self, username: str) -> bool:
        """Invalidate cached user data."""
        key = self._make_key(self.PREFIX_USER_DATA, username)
        return await self.delete(key)

    # Knowledge Base metadata caching
    async def get_kb_metadata(self, kb_id: str) -> Optional[dict]:
        """Get cached knowledge base metadata."""
        key = self._make_key(self.PREFIX_KB_METADATA, kb_id)
        return await self.get(key)

    async def set_kb_metadata(self, kb_id: str, metadata: dict) -> bool:
        """Cache knowledge base metadata."""
        key = self._make_key(self.PREFIX_KB_METADATA, kb_id)
        return await self.set(key, metadata, KB_METADATA_TTL)

    async def invalidate_kb_metadata(self, kb_id: str) -> bool:
        """Invalidate cached knowledge base metadata."""
        key = self._make_key(self.PREFIX_KB_METADATA, kb_id)
        return await self.delete(key)

    async def invalidate_all_kb_metadata(self) -> int:
        """Invalidate all cached KB metadata."""
        pattern = self._make_pattern(self.PREFIX_KB_METADATA)
        return await self.invalidate(pattern)

    # Search results caching (optional - for repeated queries)
    async def get_search_results(self, query_hash: str) -> Optional[dict]:
        """Get cached search results."""
        key = self._make_key(self.PREFIX_SEARCH_RESULTS, query_hash)
        return await self.get(key)

    async def set_search_results(self, query_hash: str, results: dict) -> bool:
        """Cache search results."""
        key = self._make_key(self.PREFIX_SEARCH_RESULTS, query_hash)
        return await self.set(key, results, SEARCH_RESULTS_TTL)

    async def invalidate_search_results(self, query_hash: str) -> bool:
        """Invalidate cached search results."""
        key = self._make_key(self.PREFIX_SEARCH_RESULTS, query_hash)
        return await self.delete(key)

    # Batch operations
    async def get_many(self, keys: List[str]) -> dict:
        """
        Batch get multiple keys.

        Args:
            keys: List of cache keys

        Returns:
            Dict mapping key to cached value (None if not found)
        """
        try:
            conn = await redis.get_redis_connection()
            values = await conn.mget(keys)

            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = None
                else:
                    result[key] = None

            return result

        except Exception as e:
            logger.warning(f"Batch cache get failed: {e}")
            return {key: None for key in keys}

    async def set_many(self, mapping: dict, ttl: int = DEFAULT_TTL) -> int:
        """
        Batch set multiple keys.

        Args:
            mapping: Dict of {key: value}
            ttl: Time-to-live in seconds

        Returns:
            Number of keys successfully cached
        """
        try:
            conn = await redis.get_redis_connection()
            pipe = conn.pipeline()

            for key, value in mapping.items():
                pipe.setex(key, ttl, json.dumps(value))

            await pipe.execute()
            logger.debug(f"Batch cached {len(mapping)} keys")
            return len(mapping)

        except Exception as e:
            logger.warning(f"Batch cache set failed: {e}")
            return 0

    async def clear_all(self) -> bool:
        """
        Clear all cached data (use with caution).

        Returns:
            True if successful
        """
        try:
            conn = await redis.get_redis_connection()
            await conn.flushdb()
            logger.warning("Cleared all cache data")
            return True

        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False


# Global cache service instance
cache_service = CacheService()
