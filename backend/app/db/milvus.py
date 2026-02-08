from pymilvus import (
    MilvusClient,
    DataType,
    AnnSearchRequest,
    RRFRanker,
    WeightedRanker,
    MilvusException,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import numpy as np
import concurrent.futures
import threading
import math
import time
from collections import defaultdict
from app.core.config import settings
from app.core.logging import logger
from app.core.circuit_breaker import vector_db_circuit


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

    @vector_db_circuit
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(MilvusException),
    )
    def _hybrid_search_with_retry(
        self, collection_name, reqs, ranker, limit, output_fields
    ):
        return self.client.hybrid_search(
            collection_name, reqs, ranker, limit, output_fields=output_fields
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(MilvusException),
    )
    def _search_with_retry(
        self, collection_name, data, anns_field, limit, output_fields, search_params
    ):
        return self.client.search(
            collection_name,
            data,
            anns_field=anns_field,
            limit=limit,
            output_fields=output_fields,
            search_params=search_params,
        )

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
                "M": settings.hnsw_m,
                "efConstruction": settings.hnsw_ef_construction,
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
        index_params.add_index(
            field_name="page_number",
            index_name="page_number_index",
            index_type="INVERTED",
        )

        self.client.create_index(
            collection_name=collection_name, index_params=index_params, sync=True
        )
        self.load_collection(collection_name)

    def ensure_pages_sparse_collection(self, patch_collection_name: str) -> str:
        """Ensure the page-level sparse sidecar collection exists.

        Creates {patch_collection_name}_pages_sparse if it doesn't exist.
        Returns the sidecar collection name.
        """
        sidecar_name = self._pages_sparse_collection_name(patch_collection_name)
        if self.client.has_collection(sidecar_name):
            return sidecar_name

        schema = self.client.create_schema(auto_id=False, enable_dynamic_fields=False)
        schema.add_field(
            field_name="page_id",
            datatype=DataType.VARCHAR,
            max_length=512,
            is_primary=True,
        )
        schema.add_field(
            field_name="sparse_vector",
            datatype=DataType.SPARSE_FLOAT_VECTOR,
        )
        schema.add_field(
            field_name="file_id",
            datatype=DataType.VARCHAR,
            max_length=65535,
        )
        schema.add_field(
            field_name="page_number",
            datatype=DataType.INT64,
        )
        schema.add_field(
            field_name="text_preview",
            datatype=DataType.VARCHAR,
            max_length=2000,
        )

        self.client.create_collection(collection_name=sidecar_name, schema=schema)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_vector_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            params={"drop_ratio_build": 0.2},
        )
        index_params.add_index(
            field_name="file_id",
            index_name="file_id_index",
            index_type="INVERTED",
        )
        index_params.add_index(
            field_name="page_number",
            index_name="page_number_index",
            index_type="INVERTED",
        )
        index_params.add_index(
            field_name="page_id",
            index_name="page_id_index",
            index_type="INVERTED",
        )
        self.client.create_index(
            collection_name=sidecar_name, index_params=index_params, sync=True
        )
        self.load_collection(sidecar_name)
        logger.info(f"Created pages_sparse sidecar collection: {sidecar_name}")
        return sidecar_name

    @vector_db_circuit
    def search(self, collection_name, data, topk, return_timing: bool = False):
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
        empty_timing = {
            "candidate_gen_ms": 0.0,
            "vector_fetch_ms": 0.0,
            "maxsim_rerank_ms": 0.0,
            "total_search_ms": 0.0,
        }

        # Load collection if not already loaded
        self.load_collection(collection_name)

        # Guard: empty queries can happen if embedding service fails or caller sends empty input.
        if not data:
            return ([], empty_timing) if return_timing else []

        # New retrieval modes (thesis): sparse recall on page-level sidecar + exact MaxSim rerank on patch vectors.
        if isinstance(data, dict) and data.get("mode") in [
            "sparse_then_rerank",
            "dual_then_rerank",
        ]:
            results, timing = self._search_sparse_then_rerank(
                patch_collection_name=collection_name,
                dense_vecs=data.get("dense_vecs") or [],
                sparse_query=data.get("sparse_query") or {},
                topk=int(topk),
                mode=str(data.get("mode")),
                ef_override=data.get("ef"),
            )
            return (results, timing) if return_timing else results

        dense_vecs = data
        sparse_vecs = []
        ef_override = None
        if isinstance(data, dict):
            dense_vecs = data.get("dense_vecs") or data.get("data") or []
            sparse_vecs = data.get("sparse_vecs") or []
            ef_override = data.get("ef")

        if not dense_vecs:
            return ([], empty_timing) if return_timing else []

        # Buffer for candidate generation (per query token vector).
        # Larger -> better recall, slower.
        search_limit = min(
            max(int(topk) * 10, settings.rag_search_limit_min),
            settings.rag_search_limit_cap,
        )

        # Perform a vector search on the collection to find the top-k most similar documents.
        # HNSW constraint: ef must be >= limit (k), so set ef = max(search_limit, 100)
        ef_value = max(search_limit, settings.rag_ef_min)
        if ef_override is not None:
            try:
                ef_value = max(int(ef_value), int(search_limit), int(ef_override))
            except Exception:
                pass
        search_params = {"metric_type": "IP", "params": {"ef": ef_value}}
        use_hybrid = (
            settings.rag_hybrid_enabled
            and _has_sparse_vectors(sparse_vecs)
            and len(sparse_vecs) == len(dense_vecs)
        )

        t_candidate_start = time.perf_counter()

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
            results = self._hybrid_search_with_retry(
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
            results = self._search_with_retry(
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

        # 1) Build approximate MaxSim scores to pick a bounded set of candidate PAGES.
        # We group by (file_id, page_number) because image_id is patch-level.
        approx_scores: dict[tuple[str, int], float] = {}
        for token_hits in results or []:
            best_per_page: dict[tuple[str, int], float] = {}
            for hit in token_hits or []:
                entity = hit.get("entity") or {}
                fid = entity.get("file_id")
                pn = entity.get("page_number")
                if fid is None or pn is None:
                    continue
                try:
                    pn_i = int(pn)
                except Exception:
                    continue
                page_key = (str(fid), pn_i)
                dist = hit.get("distance", hit.get("score", 0.0))
                prev = best_per_page.get(page_key)
                if prev is None or dist > prev:
                    best_per_page[page_key] = float(dist)

            for page_key, best in best_per_page.items():
                approx_scores[page_key] = approx_scores.get(page_key, 0.0) + float(best)

        if not approx_scores:
            candidate_gen_ms = (time.perf_counter() - t_candidate_start) * 1000.0
            timing = {
                **empty_timing,
                "candidate_gen_ms": float(candidate_gen_ms),
                "total_search_ms": float(candidate_gen_ms),
            }
            return ([], timing) if return_timing else []

        # 2) Keep only top-N candidate pages for exact reranking.
        candidate_pages_limit = min(
            max(int(topk) * 20, settings.rag_search_limit_min),
            settings.rag_candidate_images_cap,
        )
        candidate_pages = [
            (fid, pn, score)
            for (fid, pn), score in sorted(
                approx_scores.items(), key=lambda kv: kv[1], reverse=True
            )[:candidate_pages_limit]
        ]

        candidate_gen_ms = (time.perf_counter() - t_candidate_start) * 1000.0
        results, rerank_timing = self._exact_rerank_pages(
            patch_collection_name=collection_name,
            dense_vecs=dense_vecs,
            candidate_pages=candidate_pages,
            topk=int(topk),
            diversify=True,
        )

        vector_fetch_ms = float(rerank_timing.get("vector_fetch_ms", 0.0))
        maxsim_rerank_ms = float(rerank_timing.get("maxsim_rerank_ms", 0.0))
        timing = {
            "candidate_gen_ms": float(candidate_gen_ms),
            "vector_fetch_ms": vector_fetch_ms,
            "maxsim_rerank_ms": maxsim_rerank_ms,
            "total_search_ms": float(
                candidate_gen_ms + vector_fetch_ms + maxsim_rerank_ms
            ),
        }
        return (results, timing) if return_timing else results

    def _resolve_actual_collection_name(self, collection_name: str) -> str:
        """Resolve Milvus alias -> underlying collection name (no-op if not an alias)."""
        try:
            desc = self.client.describe_collection(collection_name)
            if isinstance(desc, dict):
                actual = desc.get("collection_name")
                if actual:
                    return str(actual)
            return collection_name
        except Exception:
            return collection_name

    def _pages_sparse_collection_name(self, patch_collection_name: str) -> str:
        actual = self._resolve_actual_collection_name(patch_collection_name)
        return f"{actual}{settings.rag_pages_sparse_suffix}"

    def get_page_previews(
        self, patch_collection_name: str, pairs: list[tuple[str, int]]
    ) -> dict[tuple[str, int], str]:
        """Fetch page-level text previews from the sparse sidecar collection.

        Returns:
            Dict mapping (file_id, page_number) -> text_preview
        """
        if not pairs:
            return {}

        pages_coll = self._pages_sparse_collection_name(patch_collection_name)
        if not self.client.has_collection(pages_coll):
            return {}

        # Query by page_id because it is a single scalar key and has an inverted index.
        page_ids = [f"{fid}::{int(pn)}" for fid, pn in pairs]
        previews: dict[tuple[str, int], str] = {}

        def _chunks(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        for chunk in _chunks(page_ids, 100):
            escaped = [str(x).replace("'", "\\'") for x in chunk]
            flt = "page_id in [" + ", ".join([f"'{x}'" for x in escaped]) + "]"
            rows = self.client.query(
                pages_coll,
                filter=flt,
                limit=len(chunk),
                output_fields=["file_id", "page_number", "text_preview"],
            )
            for row in rows or []:
                fid = row.get("file_id")
                pn = row.get("page_number")
                if fid is None or pn is None:
                    continue
                try:
                    pn_i = int(pn)
                except Exception:
                    continue
                previews[(str(fid), pn_i)] = str(row.get("text_preview") or "")

        return previews

    def _sparse_recall_pages(
        self, pages_sparse_collection: str, sparse_query: dict[int, float], limit: int
    ) -> list[tuple[str, int, float]]:
        """Sparse recall on page-level collection; returns [(file_id, page_number, score)]."""
        if not sparse_query:
            return []
        if not self.client.has_collection(pages_sparse_collection):
            return []

        self.load_collection(pages_sparse_collection)
        results = self._search_with_retry(
            pages_sparse_collection,
            data=[sparse_query],
            anns_field="sparse_vector",
            limit=int(limit),
            output_fields=["file_id", "page_number", "page_id"],
            search_params={"metric_type": "IP", "params": {"drop_ratio_search": 0.0}},
        )
        hits = (results or [[]])[0] if results else []
        out: list[tuple[str, int, float]] = []
        for hit in hits or []:
            ent = hit.get("entity") or {}
            fid = ent.get("file_id")
            pn = ent.get("page_number")
            if fid is None or pn is None:
                continue
            try:
                pn_i = int(pn)
            except Exception:
                continue
            score = float(hit.get("distance", hit.get("score", 0.0)) or 0.0)
            out.append((str(fid), pn_i, score))
        return out

    def _dense_approx_recall_pages(
        self, patch_collection_name: str, dense_vecs, limit: int, ef_override=None
    ) -> list[tuple[str, int, float]]:
        """Dense recall on patch vectors; returns page-level approximate MaxSim scores."""
        if not dense_vecs:
            return []
        self.load_collection(patch_collection_name)

        ef_value = max(int(limit), settings.rag_ef_min)
        if ef_override is not None:
            try:
                ef_value = max(int(ef_value), int(limit), int(ef_override))
            except Exception:
                pass
        search_params = {"metric_type": "IP", "params": {"ef": ef_value}}
        results = self._search_with_retry(
            patch_collection_name,
            dense_vecs,
            anns_field="vector",
            limit=int(limit),
            output_fields=["file_id", "page_number", "image_id"],
            search_params=search_params,
        )

        approx_scores: dict[tuple[str, int], float] = {}
        for token_hits in results or []:
            best_per_page: dict[tuple[str, int], float] = {}
            for hit in token_hits or []:
                ent = hit.get("entity") or {}
                fid = ent.get("file_id")
                pn = ent.get("page_number")
                if fid is None or pn is None:
                    continue
                try:
                    pn_i = int(pn)
                except Exception:
                    continue
                page_key = (str(fid), pn_i)
                dist = float(hit.get("distance", hit.get("score", 0.0)) or 0.0)
                prev = best_per_page.get(page_key)
                if prev is None or dist > prev:
                    best_per_page[page_key] = dist

            for page_key, best in best_per_page.items():
                approx_scores[page_key] = approx_scores.get(page_key, 0.0) + float(best)

        out = [
            (fid, pn, score)
            for (fid, pn), score in sorted(
                approx_scores.items(), key=lambda kv: kv[1], reverse=True
            )
        ]
        return out

    def _rrf_fuse(
        self,
        ranked_lists: list[list[tuple[str, int, float]]],
        k: int,
    ) -> dict[tuple[str, int], float]:
        fused: dict[tuple[str, int], float] = defaultdict(float)
        for lst in ranked_lists:
            for rank, (fid, pn, _score) in enumerate(lst, start=1):
                fused[(fid, pn)] += 1.0 / float(k + rank)
        return dict(fused)

    def _diversify_candidates(
        self,
        candidates: list[tuple[str, int, float]],
        topk: int,
    ) -> list[tuple[str, int, float]]:
        """Diversify by file_id while still allowing enough pages to satisfy topk.

        Strategy:
        - pick top N files (N = rag_diverse_file_limit)
        - for each selected file, keep up to P pages, where P ~= ceil(topk / N)
        """
        if not candidates:
            return []

        n_files = int(getattr(settings, "rag_diverse_file_limit", 20))
        if n_files <= 0:
            return candidates

        per_file_cap = int(getattr(settings, "rag_diverse_pages_per_file_cap", 3))
        per_file_pages = max(1, int(math.ceil(float(topk) / float(n_files))))
        per_file_pages = min(per_file_cap, per_file_pages)

        # Group pages by file_id, sorted by approx score
        by_file: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
        for fid, pn, score in candidates:
            by_file[str(fid)].append((str(fid), int(pn), float(score)))
        for fid in list(by_file.keys()):
            by_file[fid].sort(key=lambda x: x[2], reverse=True)

        # Rank files by their best page score.
        files_ranked = sorted(
            [(fid, pages[0][2]) for fid, pages in by_file.items() if pages],
            key=lambda x: x[1],
            reverse=True,
        )
        selected_files = [fid for fid, _ in files_ranked[:n_files]]

        diversified: list[tuple[str, int, float]] = []
        for fid in selected_files:
            diversified.extend(by_file[fid][:per_file_pages])

        # Keep stable ordering by score.
        diversified.sort(key=lambda x: x[2], reverse=True)
        return diversified

    def _diversify_with_backfill(
        self,
        candidates: list[tuple[str, int, float]],
        topk: int,
    ) -> list[tuple[str, int, float]]:
        """Diversify but still guarantee up to topk candidates when possible.

        Diversification can intentionally cap pages-per-file. When that cap makes the
        result set smaller than topk, we backfill from the remaining ranked candidates
        (preserving the diversified head ordering).
        """
        if not candidates:
            return []

        diversified = self._diversify_candidates(candidates, topk=topk)
        if len(diversified) >= int(topk):
            return diversified[: int(topk)]

        seen: set[tuple[str, int]] = {(fid, int(pn)) for fid, pn, _s in diversified}
        out = list(diversified)
        for fid, pn, score in candidates:
            key = (str(fid), int(pn))
            if key in seen:
                continue
            out.append((str(fid), int(pn), float(score)))
            seen.add(key)
            if len(out) >= int(topk):
                break
        return out

    @staticmethod
    def _distinct_files(candidates: list[tuple[str, int, float]]) -> int:
        """Count distinct file_id in a (file_id, page_number, score) list."""
        return len({str(fid) for fid, _pn, _s in (candidates or [])})

    @staticmethod
    def _distinct_pages(candidates: list[tuple[str, int, float]]) -> int:
        """Count distinct (file_id, page_number) keys in a candidate list."""
        return len({(str(fid), int(pn)) for fid, pn, _s in (candidates or [])})

    def _exact_rerank_pages(
        self,
        patch_collection_name: str,
        dense_vecs,
        candidate_pages: list[tuple[str, int, float]],
        topk: int,
        diversify: bool,
    ):
        empty_rerank_timing = {"vector_fetch_ms": 0.0, "maxsim_rerank_ms": 0.0}
        if not candidate_pages:
            return [], empty_rerank_timing
        if diversify:
            if getattr(settings, "rag_debug_retrieval", False):
                logger.info(
                    "RAG(thesis): exact_rerank input candidates=%d distinct_pages=%d distinct_files=%d",
                    len(candidate_pages),
                    self._distinct_pages(candidate_pages),
                    self._distinct_files(candidate_pages),
                )
            candidate_pages = self._diversify_with_backfill(candidate_pages, topk=topk)
            if getattr(settings, "rag_debug_retrieval", False):
                logger.info(
                    "RAG(thesis): exact_rerank after diversify+backfill candidates=%d distinct_pages=%d distinct_files=%d topk=%d",
                    len(candidate_pages),
                    self._distinct_pages(candidate_pages),
                    self._distinct_files(candidate_pages),
                    int(topk),
                )

        # Group requested pages by file_id to keep Milvus filter small and correct for (file_id,page_number) pairs.
        pages_by_file: dict[str, set[int]] = defaultdict(set)
        for fid, pn, _score in candidate_pages:
            pages_by_file[str(fid)].add(int(pn))

        page_size = 1024
        all_rows: list[dict] = []

        t_fetch_start = time.perf_counter()
        for fid, pns in pages_by_file.items():
            escaped_fid = str(fid).replace("'", "\\'")
            pn_list = ", ".join([str(int(pn)) for pn in sorted(pns)])
            filter_expr = f"file_id == '{escaped_fid}' && page_number in [{pn_list}]"

            it = self.client.query_iterator(
                collection_name=patch_collection_name,
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

        vector_fetch_ms = (time.perf_counter() - t_fetch_start) * 1000.0

        if not all_rows:
            return [], {
                "vector_fetch_ms": float(vector_fetch_ms),
                "maxsim_rerank_ms": 0.0,
            }

        # Group vectors by page.
        docs_map: dict[tuple[str, int], dict] = {}
        for row in all_rows:
            fid = row.get("file_id")
            pn = row.get("page_number")
            if fid is None or pn is None:
                continue
            try:
                pn_i = int(pn)
            except Exception:
                continue
            page_key = (str(fid), pn_i)
            entry = docs_map.get(page_key)
            if entry is None:
                entry = {
                    "vectors": [],
                    "metadata": {
                        "file_id": str(fid),
                        "page_number": pn_i,
                        # Representative patch id (debug only); do NOT treat as page id.
                        "image_id": row.get("image_id"),
                    },
                }
                docs_map[page_key] = entry
            entry["vectors"].append(row["vector"])

        query_vecs = np.asarray(dense_vecs, dtype=np.float32)

        t_rerank_start = time.perf_counter()
        scores = []
        for _page_key, doc_data in docs_map.items():
            if not doc_data["vectors"]:
                continue
            doc_vecs = np.asarray(doc_data["vectors"], dtype=np.float32)
            score = np.dot(query_vecs, doc_vecs.T).max(axis=1).sum()
            scores.append((float(score), doc_data["metadata"]))

        scores.sort(key=lambda x: x[0], reverse=True)
        maxsim_rerank_ms = (time.perf_counter() - t_rerank_start) * 1000.0

        results = [
            {
                "score": score,
                "image_id": metadata.get("image_id"),
                "file_id": metadata["file_id"],
                "page_number": metadata["page_number"],
            }
            for score, metadata in scores[: int(topk)]
        ]

        return results, {
            "vector_fetch_ms": float(vector_fetch_ms),
            "maxsim_rerank_ms": float(maxsim_rerank_ms),
        }

    def _search_sparse_then_rerank(
        self,
        patch_collection_name: str,
        dense_vecs,
        sparse_query: dict[int, float],
        topk: int,
        mode: str,
        ef_override=None,
    ):
        """Dual-candidate mode: sparse recall -> exact MaxSim rerank (optionally fused with dense recall)."""
        if not dense_vecs:
            empty_timing = {
                "candidate_gen_ms": 0.0,
                "vector_fetch_ms": 0.0,
                "maxsim_rerank_ms": 0.0,
                "total_search_ms": 0.0,
            }
            return [], empty_timing

        t_candidate_start = time.perf_counter()

        pages_sparse_coll = self._pages_sparse_collection_name(patch_collection_name)

        # Candidate generation limits: keep bounded (we'll diversify before exact rerank).
        sparse_limit = min(
            max(topk * 10, settings.rag_search_limit_min),
            settings.rag_search_limit_cap,
        )
        dense_limit = min(
            max(topk * 10, settings.rag_search_limit_min),
            settings.rag_search_limit_cap,
        )

        sparse_ranked = self._sparse_recall_pages(
            pages_sparse_collection=pages_sparse_coll,
            sparse_query=sparse_query,
            limit=sparse_limit,
        )
        if getattr(settings, "rag_debug_retrieval", False):
            logger.info(
                "RAG(thesis): mode=%s topk=%d sparse_limit=%d sparse_candidates=%d sparse_distinct_files=%d",
                str(mode),
                int(topk),
                int(sparse_limit),
                len(sparse_ranked),
                self._distinct_files(sparse_ranked),
            )

        if mode == "sparse_then_rerank":
            candidates = sparse_ranked
        elif mode == "dual_then_rerank" and not sparse_ranked:
            # Thesis safety: if the sparse sidecar is missing/unavailable, do not return
            # an empty result set. Fall back to dense approx recall then exact rerank.
            candidates = self._dense_approx_recall_pages(
                patch_collection_name=patch_collection_name,
                dense_vecs=dense_vecs,
                limit=dense_limit,
                ef_override=ef_override,
            )
            if getattr(settings, "rag_debug_retrieval", False):
                logger.info(
                    "RAG(thesis): dense_fallback dense_limit=%d dense_candidates=%d dense_distinct_files=%d",
                    int(dense_limit),
                    len(candidates),
                    self._distinct_files(candidates),
                )
        else:
            dense_ranked = self._dense_approx_recall_pages(
                patch_collection_name=patch_collection_name,
                dense_vecs=dense_vecs,
                limit=dense_limit,
                ef_override=ef_override,
            )
            if getattr(settings, "rag_debug_retrieval", False):
                logger.info(
                    "RAG(thesis): dense_stage dense_limit=%d dense_candidates=%d dense_distinct_files=%d",
                    int(dense_limit),
                    len(dense_ranked),
                    self._distinct_files(dense_ranked),
                )

            fused = self._rrf_fuse(
                ranked_lists=[sparse_ranked, dense_ranked],
                k=int(getattr(settings, "rag_hybrid_rrf_k", 60)),
            )
            # Convert fused map -> ranked list.
            candidates = [
                (fid, pn, score)
                for (fid, pn), score in sorted(
                    fused.items(), key=lambda kv: kv[1], reverse=True
                )
            ]
            if getattr(settings, "rag_debug_retrieval", False):
                logger.info(
                    "RAG(thesis): fused_candidates=%d fused_distinct_files=%d",
                    len(candidates),
                    self._distinct_files(candidates),
                )

        # Cap candidate pages before fetching patch vectors.
        candidates = candidates[
            : int(getattr(settings, "rag_candidate_images_cap", 120))
        ]
        if getattr(settings, "rag_debug_retrieval", False):
            logger.info(
                "RAG(thesis): capped_candidates=%d cap=%d distinct_files=%d",
                len(candidates),
                int(getattr(settings, "rag_candidate_images_cap", 120)),
                self._distinct_files(candidates),
            )

        candidate_gen_ms = (time.perf_counter() - t_candidate_start) * 1000.0
        results, rerank_timing = self._exact_rerank_pages(
            patch_collection_name=patch_collection_name,
            dense_vecs=dense_vecs,
            candidate_pages=candidates,
            topk=topk,
            diversify=True,
        )

        vector_fetch_ms = float(rerank_timing.get("vector_fetch_ms", 0.0))
        maxsim_rerank_ms = float(rerank_timing.get("maxsim_rerank_ms", 0.0))
        timing = {
            "candidate_gen_ms": float(candidate_gen_ms),
            "vector_fetch_ms": vector_fetch_ms,
            "maxsim_rerank_ms": maxsim_rerank_ms,
            "total_search_ms": float(
                candidate_gen_ms + vector_fetch_ms + maxsim_rerank_ms
            ),
        }
        return results, timing

    @vector_db_circuit
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


class _LazyMilvusManager:
    """Lazy wrapper around MilvusManager to avoid connecting at import time.

    Rationale:
    - Many modules import `milvus_client` for type/attribute access but do not
      actually need a live Milvus connection during import (notably unit tests).
    - Creating MilvusClient eagerly causes import-time failures when Milvus is
      not running, even if no code path uses it.
    """

    _inner: "MilvusManager | None" = None

    def _get_inner(self) -> "MilvusManager":
        if self._inner is None:
            self._inner = MilvusManager()
        return self._inner

    def __getattr__(self, name: str):
        return getattr(self._get_inner(), name)


milvus_client = _LazyMilvusManager()
