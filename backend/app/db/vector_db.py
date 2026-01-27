"""
Unified Vector Database Client Factory
Supports switching between Milvus and Qdrant based on VECTOR_DB environment variable.
"""

from app.core.config import settings
from app.core.logging import logger


class VectorDBClientWrapper:
    """
    Unified interface for Milvus and Qdrant clients.
    Provides compatibility layer for method signatures.
    """

    def __init__(self):
        vector_db = getattr(settings, "vector_db", "milvus")

        if vector_db == "qdrant":
            logger.info(f"Using Qdrant as vector database (URL: {settings.qdrant_url})")
            from app.db.qdrant import qdrant_client

            self.client = qdrant_client
            self._is_qdrant = True
        else:
            logger.info(f"Using Milvus as vector database (URI: {settings.milvus_uri})")
            from app.db.milvus import milvus_client

            self.client = milvus_client
            self._is_qdrant = False

    def check_collection(self, collection_name):
        return self.client.check_collection(collection_name)

    def create_collection(self, collection_name, dim=128):
        if self._is_qdrant:
            return self.client.create_collection(collection_name, vector_size=dim)
        return self.client.create_collection(collection_name, dim=dim)

    def insert(self, data, collection_name=None):
        """
        Unified insert method.
        For both backends, collection_name is separate argument.
        data dict must contain colqwen_vecs and metadata.
        """
        if self._is_qdrant:
            # Qdrant expects collection_name as first arg, data dict as second
            return self.client.insert_multi_vectors(collection_name, data)
        else:
            # Milvus expects collection_name as second arg, data dict as first
            return self.client.insert(data, collection_name)

    def search(self, collection_name, data, topk=10):
        """
        Unified search method.
        Both Qdrant and Milvus expect multivector query (list of token vectors).
        data shape: List[List[float]] (n_tokens, dim)
        """
        if self._is_qdrant:
            # Qdrant expects multivector query
            return self.client.search(collection_name, data, topk)
        else:
            # Milvus expects multivector query (MaxSim)
            return self.client.search(collection_name, data, topk)

    def delete_files(self, collection_name, file_ids):
        if self._is_qdrant:
            return self.client.delete_files(collection_name, file_ids)
        return self.client.delete_files(collection_name, file_ids)

    def delete_collection(self, collection_name):
        return self.client.delete_collection(collection_name)

    def delete_collections_bulk(self, collection_names):
        """Bulk delete multiple collections."""
        if self._is_qdrant:
            # Qdrant implementation - add if needed
            return self.client.delete_collections_bulk(collection_names) if hasattr(self.client, 'delete_collections_bulk') else {"deleted_count": 0, "total_requested": len(collection_names), "failed": []}
        return self.client.delete_collections_bulk(collection_names)

    def health_check(self) -> bool:
        """Check vector database health."""
        if hasattr(self.client, "health_check"):
            return self.client.health_check()
        # Fallback: assume healthy if client exists
        return True

    def __getattr__(self, name):
        """Delegate any other attributes to underlying client."""
        return getattr(self.client, name)


# Singleton instance for backward compatibility
vector_db_client = VectorDBClientWrapper()
get_vector_db_client = lambda: vector_db_client
