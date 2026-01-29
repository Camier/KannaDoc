"""
Qdrant Manager - Vector Database Operations for ColQwen/ColBERT Multi-Vectors
"""

from typing import List, Optional, Dict, Any
import numpy as np
import uuid
from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.core.logging import logger


class QdrantManager:
    """
    Manages Qdrant vector database operations for multi-vector embeddings.

    Supports:
    - Named multivectors (colbert) for ColBERT token-level embeddings
    - Native late interaction scoring with MAX_SIM comparator
    - Dense vectors for fast retrieval + multivector for reranking
    """

    def __init__(self):
        qdrant_url = getattr(settings, "qdrant_url", "http://qdrant:6333")
        self.client = QdrantClient(
            url=qdrant_url, timeout=60.0, prefer_grpc=False, check_compatibility=False
        )
        logger.info(f"Initialized Qdrant client with URL: {qdrant_url}")

    @staticmethod
    def _l2_normalize(vec):
        """Normalize vector to unit length (L2 norm)."""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return (np.array(vec) / norm).tolist()

    def create_collection(self, collection_name: str, vector_size: int = 128) -> None:
        """
        Create a Qdrant collection with multivector support for ColBERT-style embeddings.

        Args:
            collection_name: Name of the collection
            vector_size: Expected vector dimension (128 for ColQwen/ColBERT)
        """
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
                "colbert": models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM
                    ),
                    hnsw_config=models.HnswConfigDiff(m=0),
                ),
            },
        )
        logger.info(
            f"Created collection: {collection_name} with vector_size={vector_size} "
            f"(dense + colbert multivector with MAX_SIM)"
        )

    def insert_multi_vectors(
        self,
        collection_name: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Insert multivector embeddings for a single page/image.

        ONE PAGE = ONE POINT with multivector field.

        Args:
            collection_name: Name of the collection
            data: Dictionary containing:
                - colqwen_vecs: List of token vectors (List[List[float]])
                - image_id: Image identifier
                - page_number: Page number
                - file_id: Source file ID
                - chunk_text: Optional text chunk
        """
        colqwen_vecs = data.get("colqwen_vecs", [])
        image_id = data.get("image_id")
        page_number = data.get("page_number")
        file_id = data.get("file_id")
        chunk_text = data.get("chunk_text", "")

        if not colqwen_vecs:
            logger.warning(f"No vectors provided for image_id={image_id}")
            return

        # Compute dense proxy vector (mean-pool of token vectors) and L2-normalize
        dense_vec = np.mean(np.vstack(colqwen_vecs), axis=0).tolist()
        dense_vec = self._l2_normalize(dense_vec)

        # Stable point ID for idempotent ingestion (UUIDv5 from file:page)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file_id}:{page_number}"))

        point = models.PointStruct(
            id=point_id,
            vector={
                "dense": dense_vec,
                "colbert": colqwen_vecs,
            },
            payload={
                "file_id": file_id,
                "image_id": image_id,
                "page": page_number,
                "chunk_text": chunk_text,
            },
        )

        self.client.upsert(collection_name=collection_name, points=[point])
        logger.info(
            f"Inserted point for {file_id}:{page_number} "
            f"({len(colqwen_vecs)} colbert vectors + 1 dense vector)"
        )

    def search(
        self,
        collection_name: str,
        query_token_vecs: List[List[float]],
        topk: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search using 2-stage query: dense prefetch + colbert rerank.

        Args:
            collection_name: Name of the collection
            query_token_vecs: Multi-vector embeddings for query (List[List[float]])
            topk: Top-K results to return

        Returns:
            List of search results with metadata
        """
        # Compute dense proxy from query token vectors and L2-normalize
        query_dense = np.mean(np.vstack(query_token_vecs), axis=0).tolist()
        query_dense = self._l2_normalize(query_dense)

        # 2-stage query: dense prefetch (fast) -> colbert rerank (accurate)
        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_dense,
                    using="dense",
                    limit=200,
                )
            ],
            query=query_token_vecs,
            using="colbert",
            limit=topk,
            with_payload=True,
        )

        formatted_results = []
        for hit in results.points:
            payload = hit.payload or {}
            formatted_results.append(
                {
                    "score": hit.score,
                    "image_id": payload.get("image_id"),
                    "file_id": payload.get("file_id"),
                    "page_number": payload.get("page"),
                }
            )

        logger.info(f"Search returned {len(formatted_results)} results")
        return formatted_results

    def check_collection(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            return self.client.collection_exists(collection_name)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error checking collection {collection_name}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error checking collection {collection_name}")
            raise

    def load_collection(self, collection_name: str):
        """Load collection into memory (no-op for Qdrant)."""
        # Qdrant collections are always loaded, so this is a no-op
        logger.debug(f"Qdrant collection {collection_name} is always loaded")

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error deleting collection {collection_name}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting collection {collection_name}")
            raise

    def delete_collections_bulk(self, collection_names: List[str]) -> dict:
        """
        Bulk delete multiple collections efficiently.

        Args:
            collection_names: List of collection names to delete

        Returns:
            Dict with deletion statistics
        """
        deleted_count = 0
        failed_collections = []

        for collection_name in collection_names:
            try:
                self.client.delete_collection(collection_name)
                deleted_count += 1
                logger.info(f"Deleted collection: {collection_name}")
            except (ConnectionError, TimeoutError) as e:
                failed_collections.append({"collection": collection_name, "error": str(e)})
                logger.error(f"Connection error deleting collection {collection_name}: {e}")
            except Exception as e:
                failed_collections.append({"collection": collection_name, "error": str(e)})
                logger.error(f"Error deleting collection {collection_name}: {e}")

        return {
            "deleted_count": deleted_count,
            "total_requested": len(collection_names),
            "failed": failed_collections,
        }

    def delete_files(self, collection_name: str, image_ids: List[str]) -> bool:
        """
        Delete vectors for specific file IDs.

        Args:
            collection_name: Name of the collection
            image_ids: List of file IDs to delete (payload field 'file_id')

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_id",
                            match=models.MatchValue(any=True, values=image_ids),
                        )
                    ]
                ),
            )
            logger.info(f"Deleted {len(image_ids)} files from {collection_name}")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error deleting files: {e}")
            return False
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid input deleting files: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting files")
            raise

    def health_check(self) -> bool:
        """Check Qdrant health via /healthz endpoint."""
        try:
            import httpx

            # Use the base URL from client's REST URI
            base_url = self.client._client.rest_uri
            response = httpx.get(f"{base_url}/healthz", timeout=5.0)
            return response.status_code == 200
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Qdrant health check connection failed: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error in Qdrant health check")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection information."""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "vector_count": info.points_count,
                "vectors_config": info.config.params.vectors,
            }
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error getting collection info: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting collection info")
            return None


# Global instance (singleton pattern)
qdrant_client = QdrantManager()
