# RAG Pipeline Audit Report — 2026-02-02

Verified, evidence-based audit of the LAYRA (KannaDoc) RAG pipeline.
Counts below are a snapshot; see `AGENTS.md` for the canonical corpus size statement.

## Verified Counts

| Asset | Count | Evidence |
|-------|-------|----------|
| **Source PDFs** | 129 | `ls /LAB/@thesis/layra/backend/data/pdfs/*.pdf | wc -l` |
| **Extraction folders** | 129 | `ls -d /LAB/@thesis/layra/backend/data/extractions/*/ | wc -l` |
| **normalized.json files** | 129 | `find /LAB/@thesis/layra/backend/data/extractions -name "normalized.json" | wc -l` |
| **entities.json files** | 129 | `find /LAB/@thesis/layra/backend/data/extractions -name "entities.json" | wc -l` |
| **Milvus patch vectors** | 3,561,575 | `default.colpali_kanna_128` collection |
| **Milvus sparse pages** | 4,691 | `default.colpali_kanna_128_pages_sparse` collection |

## Link 1: PDF Source

| Aspect | Evidence |
|--------|----------|
| **Location** | `/LAB/@thesis/layra/backend/data/pdfs/` |
| **Count** | **129 PDFs** |
| **Date range** | 1857–2025 |
| **Status** | HEALTHY |

## Link 2: PDF Parsing (DataLab Marker API)

| Aspect | Evidence |
|--------|----------|
| **API Endpoint** | `https://www.datalab.to/api/v1/marker/` |
| **Proof** | Each extraction folder includes `raw/attempt1_check_url.txt` (example: `layra/backend/data/extractions/.../raw/attempt1_check_url.txt`) |
| **API Response** | Each extraction folder includes `raw/result.json` and `raw/attempt1_final_result.json` |
| **Mode** | `accurate` with `json,html,markdown,chunks` output |
| **Status** | HEALTHY — 129/129 processed |

**Note**: PDF text extraction uses the **DataLab SaaS API** (external dependency). Visual RAG (PDF to images) is handled locally by `pdf2image`.

## Link 3: Normalization

| Aspect | Evidence |
|--------|----------|
| **Output** | `normalized.json` per document |
| **Keys** | `doc_id`, `metadata`, `provenance`, `datalab`, `raw`, `chunks`, `images`, `figures` |
| **Chunks per doc** | ~200-300 (varies by doc) |
| **Chunk schema** | `chunk_id`, `doc_id`, `text`, `html`, `page_refs`, `block_ids` |
| **Status** | HEALTHY — 129/129 normalized |

## Link 4: Entity Extraction

| Aspect | Evidence |
|--------|----------|
| **Extractor** | `legacy-migration` (migrated from V1) |
| **Schema Version** | `2.0` |
| **Sample output** | Schultes 1970: 480 entities, 0 relationships |
| **Entity types found** | `Compound`, `Indication`, `Taxon`, `Concentration`, `PharmEffect` |
| **Relationships** | **0** (not populated) |
| **Status** | PARTIAL — Entities exist, relationships empty |

**Issue**: Current entities are **migrated V1 data**, not fresh MiniMax M2.1 extractions. Relationships are not populated.

## Link 5: Milvus Vector Storage

| Aspect | Evidence |
|--------|----------|
| **Connection (thesis default)** | `MILVUS_URI=http://host.docker.internal:19530` (from `layra/.env`) |
| **Host service** | Thesis uses a Milvus instance running on the host (not the `milvus-standalone` container) |
| **Fallback (if MILVUS_URI unset)** | `MILVUS_URI=${MILVUS_URI:-http://milvus-standalone:19530}` (docker-compose default) |
| **Database** | `default` (thesis corpus) and `misc` (non-thesis collections) |
| **Patch (ColPali) collection** | `default.colpali_kanna_128` (3,561,575 vectors) |
| **Page sparse sidecar** | `default.colpali_kanna_128_pages_sparse` (4,691 rows) |
| **Vector dim** | 128 (ColQwen) |
| **Unique files indexed** | 129 |
| **Status** | HEALTHY |

### Naming Drift Clarification (Important)

- The backend often refers to the thesis KB as a `colqwen...` name (derived from the knowledge base id).
- In this environment, that `colqwen...` is a **Milvus alias** that points to the underlying patch collection:
  `colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1` -> `colpali_kanna_128`.
- The page-level sparse collection is derived from the **underlying** collection name using:
  `RAG_PAGES_SPARSE_SUFFIX=_pages_sparse`.

### Page Identity vs Patch Identity

- `image_id` is **patch-level** (one row per patch vector in `default.colpali_kanna_128`); it is not a stable page identifier.
- Page grouping MUST be done on `(file_id, page_number)` for correct page-level recall, reranking, and diversification.
- `image_id` can be kept as a **debug-only** representative patch id (helpful for tracing) but should not be treated as a page id.

### Scalar Indexes (Metadata)

To keep filtering and page grouping fast without moving/copying any vectors, the patch collection should have scalar indexes:
- `INVERTED` on `file_id`
- `INVERTED` on `image_id`
- `INVERTED` on `page_number`

For existing collections, see `backend/scripts/milvus_ensure_scalar_indexes.py` (idempotent; no drops, no re-ingestion).

## Link 6: Neo4j Graph Storage

| Aspect | Evidence |
|--------|----------|
| **Config** | Commented out in `config.py` |
| **Environment** | No entries in `.env` |
| **Container** | Not deployed |
| **Script** | `neo4j_ingest.py` exists but unused |
| **Status** | DISABLED |

## Link 7: Retrieval

| Aspect | Evidence |
|--------|----------|
| **Method** | MaxSim reranking on ColQwen patch vectors (ColPali-style) |
| **Endpoint (chat RAG)** | `POST /api/v1/sse/chat` |
| **Endpoint (debug, no LLM)** | `POST /api/v1/kb/knowledge-base/{kb_id}/search-preview` |
| **Preview assets (thesis-only)** | `GET /api/v1/thesis/page-image` and `GET /api/v1/thesis/pdf` (served from local `backend/data/pdfs/`) |
| **Implementation** | `app/db/milvus.py:MilvusManager.search()` |
| **Retry logic** | Tenacity (3 attempts, 2-30s backoff) |
| **Modes** | `dense` / `hybrid` / `sparse_then_rerank` / `dual_then_rerank` |
| **Mode toggle (default)** | `RAG_RETRIEVAL_MODE` (runtime env; thesis default: `dual_then_rerank`) |
| **Sparse recall** | Uses the page-level collection `*_pages_sparse` then reranks on `colpali_kanna_128` |
| **Sparse query** | Generated via `app/rag/get_embedding.py:get_sparse_embeddings()` (`POST {MODEL_SERVER_URL}/embed_sparse`; graceful fallback to dense-only on failure) |
| **Diversification** | Candidates are diversified by `file_id` before exact rerank (with backfill to reach `top_K` pages when possible) |
| **Status** | ENABLED (thesis defaults) |

### Debug Preview (search-preview) and “Missing Metadata” Behavior

In the thesis environment, `search-preview` is used by the frontend knowledge base UI to debug retrieval. It returns per-result:
- `file_id`, `page_number`, `image_id` (patch-level representative id, debug only)
- `filename` and `minio_url` (historical field name; the UI renders it as an `<img src=...>`)

Important operational detail:
- Milvus `file_id` values for thesis are typically **human-readable PDF stems** (e.g. `"1998 - al. - Depression in Parkinsons disease an EEG frequency analysis study"`).
- Mongo `knowledge_bases.files[*].file_id` values may not match those stems (e.g. `miko_<uuid>` style), and some deployments do not populate the `files` collection at all.

To keep `search-preview` functional without re-ingestion or moving any vectors, the backend supports a thesis-only fallback:
- If Mongo file/image metadata cannot be resolved, `search-preview` returns a preview image URL using:
  `GET /api/v1/thesis/page-image?file_id=...&page_number=...&dpi=150`
- This endpoint renders directly from the local PDFs in `backend/data/pdfs/` via `pdf2image`.
- PDFs can also be fetched for debugging via:
  `GET /api/v1/thesis/pdf?file_id=...`

### Retrieval Defaults (Thesis)

- `top_K`: If the runtime mode is `sparse_then_rerank` or `dual_then_rerank`, `top_K` is normalized with a minimum of `RAG_SEARCH_LIMIT_MIN` (default: 50) to prevent accidental “2 sources only” caps from legacy UI defaults. This applies to chat RAG and the `search-preview` debug endpoint.
- `score_threshold`: `-1` is treated as “use environment default”; in thesis this defaults to `RAG_DEFAULT_SCORE_THRESHOLD=0.0` (no filtering). Set an explicit positive threshold only when you want to aggressively prune candidates.
- `search-preview overrides`: `search-preview` accepts `retrieval_mode` (optional override) and `min_score` (explicit filter for preview only). In absence of `retrieval_mode`, it uses `RAG_RETRIEVAL_MODE`.
- `dual_then_rerank` safety: if the page sparse sidecar is missing/unavailable or sparse recall returns an empty list, thesis falls back to dense approximate page recall, then applies the same exact MaxSim rerank on patch vectors.
- `sparse_then_rerank` expectation: this mode is intentionally “sparse-only” for candidate generation; if the sparse sidecar is missing or sparse recall yields no candidates, it can return an empty result set.
- Debugging: set `RAG_DEBUG_RETRIEVAL=1` to log candidate counts and distinct `file_id` stats through the sparse/dense/fuse/diversify/rerank stages (no secrets logged).

## Link 8: Evaluation System

| Aspect | Evidence |
|--------|----------|
| **Endpoint** | `POST /api/v1/eval/run` |
| **Metrics** | MRR, NDCG@K, Precision@K, Recall@K, p95 latency |
| **Labeler** | LLM-based relevance scoring (0-3 scale) |
| **Thresholds** | `recall>=0.70`, `mrr>=0.65`, `p95<=2500ms` |
| **Status** | CODE READY |

## External Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| **DataLab Marker API** | PDF text extraction | Yes (for text pipeline) |
| **MiniMax M2.1 API** | Entity extraction | Yes (for fresh extraction) |
| **Jina API** | Text embeddings (optional) | No (ColQwen is local) |

## Known Issues

1. **Entity relationships empty** — V1 migration didn't preserve relationships
2. **Neo4j disabled** — Graph storage not integrated into retrieval
3. **External API dependency** — DataLab required for text extraction
4. **Legacy entities** — Need re-extraction with MiniMax M2.1

## Recommendations

1. **Re-run entity extraction** with MiniMax M2.1 to populate relationships
2. **Enable Neo4j** if graph-based retrieval is needed
3. **Document external dependencies** clearly in deployment docs
4. **Add offline PDF parsing** option (e.g., local Marker or PyMuPDF)
