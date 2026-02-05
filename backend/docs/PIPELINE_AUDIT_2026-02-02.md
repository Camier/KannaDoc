# RAG Pipeline Audit Report — 2026-02-02

Verified, evidence-based audit of the LAYRA (KannaDoc) RAG pipeline.
Counts below are a snapshot; see `AGENTS.md` for the canonical corpus size statement.

## Verified Counts

| Asset | Count | Evidence |
|-------|-------|----------|
| **Source PDFs** | 129 | `ls /data/pdfs/*.pdf | wc -l` |
| **Extraction folders** | 129 | `ls -d /data/extractions/*/` |
| **normalized.json files** | 129 | `find ... -name "normalized.json"` |
| **entities.json files** | 129 | `find ... -name "entities.json"` |
| **Milvus vectors** | 3,561,575 | `colpali_kanna_128` collection |
| **Unique files in Milvus** | 129 | Iterated all vectors |

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
| **Proof** | `raw/attempt1_check_url.txt` contains DataLab URLs |
| **API Response** | `raw/result.json` (~1.6MB per doc) |
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
| **Connection** | `http://milvus-standalone:19530` |
| **Container** | `layra-milvus-standalone` (healthy) |
| **Visual RAG collection** | `colpali_kanna_128` (3,561,575 vectors) |
| **Text collections** | `ethnopharmacology_v2` (566 vectors) |
| **Vector dim** | 128 (ColQwen) |
| **Unique files indexed** | 129 |
| **Status** | HEALTHY |

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
| **Method** | MaxSim reranking on ColQwen vectors |
| **Endpoint** | `POST /api/v1/kb/search` |
| **Implementation** | `app/db/milvus.py:MilvusManager.search()` |
| **Retry logic** | Tenacity (3 attempts, 2-30s backoff) |
| **Hybrid search** | Available but disabled by default |
| **Status** | CODE READY — Runtime depends on backend |

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
