from pymilvus import (
    MilvusClient,
    DataType,
    AnnSearchRequest,
    RRFRanker,
    WeightedRanker,
)
import numpy as np
import concurrent.futures
import threading
from app.core.config import settings


def get_ranker(settings):
    if settings.rag_hybrid_ranker == "rrf":
        return RRFRanker(k=settings.rag_hybrid_rrf_k)
    return WeightedRanker(
        settings.rag_hybrid_dense_weight,
        settings.rag_hybrid_sparse_weight,
    )


def _has_sparse_vectors(sparse_vecs):
    if not sparse_vecs:
        return False
    for vec in sparse_vecs:
        if isinstance(vec, dict):
            if vec:
                return True
        elif vec:
            return True
    return False


class MilvusManager:
    def __init__(self):
        self.client = MilvusClient(uri=settings.milvus_uri)
        self._loaded_collections = set()
        self._load_lock = threading.Lock()

    def delete_collection(self, collection_name: str):
        if self.client.has_collection(collection_name):
            self.client.drop_collection(collection_name)
            return True
        else:
            return False

    def delete_collections_bulk(self, collection_names: list):
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
                if self.client.has_collection(collection_name):
                    self.client.drop_collection(collection_name)
                    deleted_count += 1
            except Exception as e:
                failed_collections.append(
                    {"collection": collection_name, "error": str(e)}
                )

        return {
            "deleted_count": deleted_count,
            "total_requested": len(collection_names),
            "failed": failed_collections,
        }

    def delete_files(self, collection_name: str, file_ids: list):
        if not file_ids:
            return {"deleted_count": 0}

        # Milvus filter syntax is sensitive; avoid trailing commas.
        escaped_ids = [str(fid).replace("'", "\\'") for fid in file_ids]
        filter = "file_id in [" + ", ".join([f"'{fid}'" for fid in escaped_ids]) + "]"
        res = self.client.delete(
            collection_name=collection_name,
            filter=filter,
        )
        return res

    def check_collection(self, collection_name: str):
        if self.client.has_collection(collection_name):
            return True
        else:
            return False

    def load_collection(self, collection_name: str):
        """Load collection into memory for search."""
        if not settings.rag_load_collection_once:
            self.client.load_collection(collection_name)
            return

        if collection_name in self._loaded_collections:
            return

        with self._load_lock:
            if collection_name in self._loaded_collections:
                return
            self.client.load_collection(collection_name)
            self._loaded_collections.add(collection_name)

    def create_collection(self, collection_name: str, dim: int = 128) -> None:
        if self.client.has_collection(collection_name):
            self.client.drop_collection(collection_name)

        schema = self.client.create_schema(
            auto_id=True,
            enable_dynamic_fields=True,
        )
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field(
            field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR
        )
        schema.add_field(
            field_name="image_id", datatype=DataType.VARCHAR, max_length=65535
        )
        schema.add_field(field_name="page_number", datatype=DataType.INT64)
        schema.add_field(
            field_name="file_id", datatype=DataType.VARCHAR, max_length=65535
        )

        self.client.create_collection(collection_name=collection_name, schema=schema)
        self._create_index(collection_name)

    def _create_index(self, collection_name):
        # Create an index on the vector field to enable fast similarity search.
        # Releases and drops any existing index before creating a new one with specified parameters.
        self.client.release_collection(collection_name=collection_name)
        self.client.drop_index(collection_name=collection_name, index_name="vector")
        self.client.drop_index(
            collection_name=collection_name, index_name="sparse_vector"
        )

        # Dense vector index
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_name="vector_index",
            index_type="HNSW",  # or any other index type you want
            metric_type="IP",  # or the appropriate metric type
            params={
                "M": 48,
                "efConstruction": 1024,
            },  # Optimized for ethnopharmacology medical content
        )

        # Sparse vector index
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_vector_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            params={"drop_ratio_build": 0.2},
        )

        # Scalar indexes for fast filtering and deletion
        index_params.add_index(
            field_name="file_id",
            index_name="file_id_index",
            index_type="INVERTED",
        )
        index_params.add_index(
            field_name="image_id",
            index_name="image_id_index",
            index_type="INVERTED",
        )

        self.client.create_index(
            collection_name=collection_name, index_params=index_params, sync=True
        )
        self.load_collection(collection_name)

    def search(self, collection_name, data, topk):
        """
        Perform multi-vector (MaxSim) search.

        NOTE: We keep the multimodal retrieval behavior (ColQwen page-image vectors)
        and only improve correctness/perf of the reranking stage.

        Args:
            collection_name: Name of collection to search
            data: Query vectors
            topk: Number of results to return (respected instead of hardcoded value)

        Returns:
            List of top-k search results with metadata
        """
        # Load collection if not already loaded
        self.load_collection(collection_name)

        # Guard: empty queries can happen if embedding service fails or caller sends empty input.
        if not data:
            return []

        dense_vecs = data
        sparse_vecs = []
        if isinstance(data, dict):
            dense_vecs = data.get("dense_vecs") or data.get("data") or []
            sparse_vecs = data.get("sparse_vecs") or []

        if not dense_vecs:
            return []

        # Buffer for candidate generation (per query token vector).
        # Larger -> better recall, slower.
        search_limit = min(
            max(int(topk) * 10, settings.rag_search_limit_min),
            settings.rag_search_limit_cap,
        )

        # Perform a vector search on the collection to find the top-k most similar documents.
        # HNSW constraint: ef must be >= limit (k), so set ef = max(search_limit, 100)
        ef_value = max(search_limit, settings.rag_ef_min)
        search_params = {"metric_type": "IP", "params": {"ef": ef_value}}
        use_hybrid = (
            settings.rag_hybrid_enabled
            and _has_sparse_vectors(sparse_vecs)
            and len(sparse_vecs) == len(dense_vecs)
        )

        if use_hybrid:
            dense_req = AnnSearchRequest(
                data=dense_vecs,
                anns_field="vector",
                param=search_params,
                limit=int(search_limit),
            )
            sparse_req = AnnSearchRequest(
                data=sparse_vecs,
                anns_field="sparse_vector",
                param={"metric_type": "IP", "params": {"drop_ratio_search": 0.0}},
                limit=int(search_limit),
            )
            results = self.client.hybrid_search(
                collection_name,
                [dense_req, sparse_req],
                get_ranker(settings),
                limit=int(search_limit),
                output_fields=[
                    "image_id",
                    "page_number",
                    "file_id",
                ],
            )
        else:
            results = self.client.search(
                collection_name,
                dense_vecs,
                anns_field="vector",  # Required when collection has multiple vector fields
                limit=int(search_limit),
                output_fields=[
                    "image_id",
                    "page_number",
                    "file_id",
                ],  # Remove 'vector' - fetched during reranking only
                search_params=search_params,
            )

        # 1) Build approximate MaxSim scores to pick a bounded set of candidate pages.
        # results is a list per query token vector.
        approx_scores = {}
        for token_hits in results or []:
            best_per_image = {}
            for hit in token_hits or []:
                entity = hit.get("entity") or {}
                img_id = entity.get("image_id")
                if not img_id:
                    continue
                # MilvusClient uses "distance" for similarity score (inner product here).
                dist = hit.get("distance", hit.get("score", 0.0))
                prev = best_per_image.get(img_id)
                if prev is None or dist > prev:
                    best_per_image[img_id] = dist

            for img_id, best in best_per_image.items():
                approx_scores[img_id] = approx_scores.get(img_id, 0.0) + float(best)

        if not approx_scores:
            return []

        # 2) Keep only top-N candidate pages for exact reranking.
        candidate_images_limit = min(
            max(int(topk) * 20, settings.rag_search_limit_min),
            settings.rag_candidate_images_cap,
        )
        candidate_image_ids = [
            img_id
            for img_id, _score in sorted(
                approx_scores.items(), key=lambda kv: kv[1], reverse=True
            )[:candidate_images_limit]
        ]

        # 3) Fetch ALL vectors for candidate pages.
        def _chunks(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        page_size = 1024
        all_rows = []

        for chunk_ids in _chunks(candidate_image_ids, 50):
            escaped = [str(x).replace("'", "\\'") for x in chunk_ids]
            filter_expr = "image_id in [" + ", ".join([f"'{x}'" for x in escaped]) + "]"

            it = self.client.query_iterator(
                collection_name=collection_name,
                filter=filter_expr,
                output_fields=["vector", "image_id", "page_number", "file_id"],
                batch_size=page_size,
            )
            try:
                while True:
                    batch = it.next()
                    if not batch:
                        break
                    all_rows.extend(batch)
            finally:
                it.close()

        if not all_rows:
            return []

        # 4) Group vectors by image_id.
        docs_map = {}
        for row in all_rows:
            img_id = row.get("image_id")
            if not img_id:
                continue
            entry = docs_map.get(img_id)
            if entry is None:
                entry = {
                    "vectors": [],
                    "metadata": {
                        "image_id": img_id,
                        "file_id": row.get("file_id"),
                        "page_number": row.get("page_number"),
                    },
                }
                docs_map[img_id] = entry
            entry["vectors"].append(row["vector"])

        query_vecs = np.asarray(dense_vecs, dtype=np.float32)

        # 5) Exact MaxSim reranking on candidates.
        scores = []
        for img_id, doc_data in docs_map.items():
            if not doc_data["vectors"]:
                continue
            doc_vecs = np.asarray(doc_data["vectors"], dtype=np.float32)
            # dot shape: (N_q, N_d)
            score = np.dot(query_vecs, doc_vecs.T).max(axis=1).sum()
            scores.append((float(score), doc_data["metadata"]))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "score": score,
                "image_id": metadata["image_id"],
                "file_id": metadata["file_id"],
                "page_number": metadata["page_number"],
            }
            for score, metadata in scores[: int(topk)]
        ]

    def insert(self, data, collection_name):
        # Insert ColQwen embeddings and metadata for a document into the collection.
        colqwen_vecs = [vec for vec in data["colqwen_vecs"]]
        sparse_vecs = data.get("sparse_vecs", [])
        seq_length = len(colqwen_vecs)

        # Handle sparse vectors - if not present, use empty dicts or None depending on requirement
        # But pymilvus requires the field to match schema if defined.
        # If input doesn't have sparse vectors, we might insert empty sparse vectors or handle separately.
        # For now, we assume if the collection has the field, we insert it.
        # Note: sparse vector format in pymilvus is usually dict {index: value}

        insert_data = []
        for i in range(seq_length):
            row = {
                "vector": colqwen_vecs[i],
                "image_id": data["image_id"],
                "page_number": data["page_number"],
                "file_id": data["file_id"],
            }
            # Add sparse vector if available for this token (unlikely for ColBERT)
            # or if provided at page level.
            # Assuming sparse_vecs matches colqwen_vecs length if provided,
            # OR we insert a dummy sparse vector if strict schema.
            # However, inserting "None" might fail if field is not nullable.
            # Best practice: Insert empty sparse vector {} if not present.
            if sparse_vecs and i < len(sparse_vecs):
                row["sparse_vector"] = sparse_vecs[i]
            else:
                row["sparse_vector"] = {}  # Empty sparse vector

            insert_data.append(row)

        self.client.insert(
            collection_name,
            insert_data,
        )

    def health_check(self) -> bool:
        """Check Milvus connection health."""
        try:
            # Simple check: list collections
            _ = self.client.list_collections()
            return True
        except Exception:
            return False


milvus_client = MilvusManager()
