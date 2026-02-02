# LAYRA (KannaDoc) - Agent Knowledge Base

Academic research fork for thesis work on retrieval evaluation and visual RAG optimization.

## 1. PROJECT OVERVIEW

| Aspect | Details |
|--------|---------|
| **Purpose** | Ethnopharmacology RAG system with evaluation framework |
| **Corpus** | 129 PDFs with legacy-migrated V2 entities (re-extraction recommended) |
| **Status** | DataLab fully merged; 129 docs extracted and indexed |
| **Stack** | FastAPI + Milvus + MiniMax M2.1 (Neo4j disabled) |
| **Upstream** | [liweiphys/layra](https://github.com/liweiphys/layra) |

This system is optimized for high-precision retrieval from academic PDFs, specifically focusing on ethnobotanical and pharmacological data. It consolidates the original LAYRA RAG framework with the DataLab extraction pipeline, providing a unified end-to-end research platform for "PDF-to-Knowledge" transformation. The architecture is designed to support academic research in the field of ethnopharmacology by providing a robust retrieval and evaluation harness for specialized document sets.

## 2. DIRECTORY STRUCTURE

```text
layra/
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── api/                # REST API
│   │   │   ├── endpoints/      # Resource endpoints
│   │   │   │   ├── eval.py     # Evaluation API (Run/Status/Metrics)
│   │   │   │   └── knowledge.py# KB management (Upload/Delete/List)
│   │   │   └── middleware/     # CORS and Auth Logic
│   │   └── eval/               # Evaluation system
│   │       ├── metrics.py      # MRR, NDCG, P@K, R@K implementation
│   │       ├── labeler.py      # LLM-based relevance scoring
│   │       ├── runner.py       # Orchestration + p95 latency tracking
│   │       ├── dataset.py      # Dataset CRUD and persistence
│   │       ├── query_generator.py # Synthetic query generation
│   │       └── config/
│   │           ├── thresholds.yaml    # Quality targets (dev/prod)
│   │           └── dataset_dev.jsonl  # 20 curated eval questions
│   │
│   ├── lib/
│   │   ├── entity_extraction/  # V2 extraction logic
│   │   │   ├── schemas.py      # 15 entity types, 6 relationships
│   │   │   ├── extractor.py    # MiniMax M2.1 implementation
│   │   │   ├── prompt.py       # Extraction prompt engineering
│   │   │   └── AGENTS.md       # Module documentation
│   │   └── datalab/            # Archived DataLab pipeline (11 modules)
│   │       ├── datalab_api.py  # DataLab API client (Marker API)
│   │       ├── datalab_process.py# PDF-to-block transformation
│   │       ├── normalization.py# Entity name sanitization
│   │       ├── evidence_gate.py# Confidence-based filtering
│   │       ├── section_extractor.py# Academic section identification
│   │       ├── batch_extractor.py# Directory processing logic
│   │       ├── block_index.py  # Local search indexing
│   │       ├── datalab_ingest.py # SHA256 tracking and catalog
│   │       ├── datalab_utils.py # Shared utility functions
│   │       ├── schemas/        # Pydantic data models
│   │       └── repair/         # Layout correction modules
│   │
│   ├── scripts/
│   │   └── datalab/            # Data orchestration (14 scripts)
│   │       ├── extract_entities_v2.py   # V2 entity extraction CLI
│   │       ├── migrate_entities_v2.py   # V1→V2 schema migration
│   │       ├── milvus_ingest.py         # Vector database ingestion
│   │       ├── neo4j_ingest.py          # Graph ingestion (disabled)
│   │       ├── aggregate_corpus.py      # Aggregating metadata
│   │       ├── create_id_mapping.py     # doc_id ↔ file_id mapping
│   │       ├── rag_eval.py              # CLI evaluation tool
│   │       ├── rag_optimize.py          # HNSW parameter tuning
│   │       ├── verify_merge.py          # Data integrity checks
│   │       ├── recover_extractions.py   # Recovery utilities
│   │       ├── tidy_data.py             # Data cleanup scripts
│   │       ├── consolidate_archive.py   # Archive consolidation
│   │       ├── entity_extract.py        # (Deprecated) V1 extraction
│   │       └── entity_extract_gemini.py # (Deprecated) Gemini test
│   │
│   └── data/
│       ├── pdfs/               # 129 source PDFs
│       ├── extractions/        # 129 docs with V2 entities + blocks
│       ├── corpus/             # biblio_corpus.jsonl + metadata
│       ├── id_mapping.json     # doc_id ↔ file_id mapping
│       ├── .minimax_api_key    # MiniMax API credentials
│       └── .datalab_api_key    # Legacy credentials
│
├── frontend/                   # React/Next.js frontend
├── docs/                       # Technical documentation
├── README.md                   # User-facing guide
└── AGENTS.md                   # This file
```

## 3. ENTITY EXTRACTION (V2)

**Status**: Entities are **legacy-migrated** from V1 format. Fresh extraction with MiniMax M2.1 is recommended for improved precision. Relationships are not yet populated.

15 entity types across 5 domains:

| Domain | Types |
|--------|-------|
| Ethnographic | Culture, TraditionalUse, Preparation |
| Botanical | Taxon, PlantPart, RawMaterial |
| Chemical | CompoundClass, Compound, Concentration |
| Pharmacological | Target, Mechanism, PharmEffect |
| Clinical | Indication, Evidence, Study |

6 relationship types: `TRANSFORMS`, `CONTAINS`, `ACTS_ON`, `PRODUCES`, `TREATS`, `SUGGESTS`.

**Detailed docs**: `backend/lib/entity_extraction/AGENTS.md`  
**Audit report**: `backend/docs/PIPELINE_AUDIT_2026-02-02.md`

## 4. DATALAB PIPELINE

The DataLab extraction pipeline has been consolidated into LAYRA to provide a unified data processing flow. It handles the transformation of raw PDFs into structured knowledge blocks using layout-aware parsing (via Marker API).

**Key Modules (`backend/lib/datalab/`):**
- `datalab_process.py`: Handles core PDF-to-Block conversion using layout-aware extraction. It manages the full lifecycle of a document extraction session, from upload to polling and result retrieval.
- `normalization.py`: Sanitizes entity names and properties to ensure KB consistency. It maps raw Marker API outputs to the unified `NormalizedDocumentV2` schema, handling asset persistence.
- `evidence_gate.py`: Filters extracted entities based on textual evidence confidence scores, preventing low-quality or hallucinated entities from entering the vector store.
- `section_extractor.py`: Identifies academic sections (e.g., Introduction, Methods, Results, Discussion) using a combination of keyword heuristics and layout cues.
- `batch_extractor.py`: Orchestrates large-scale processing of document directories using thread pools, enabling high-throughput extraction of the entire corpus.
- `block_index.py`: Manages indexing of text blocks with spatial metadata (bbox, polygon), allowing for visual verification of retrieved chunks in downstream applications.
- `datalab_api.py`: Robust client for Marker API with exponential backoff, result unpacking, and automatic handling of rate limits and session timeouts.
- `datalab_ingest.py`: Catalog manager that tracks documents using SHA256 hashes to ensure idempotency and avoid redundant API calls for unchanged files.
- `datalab_utils.py`: Shared utilities for path sanitization, hashing, and atomic file writes to ensure data integrity during parallel operations.
- `repair/`: Sub-package containing logic for fixing common OCR/layout artifacts and backfilling missing metadata like DOI or Publication Year from external APIs.
- `schemas/`: Pydantic data models for type safety across the pipeline, including `NormalizedDocumentV2`, `ImageAsset`, and `FigureRecord`.

The pipeline transforms raw PDFs into a structured representation that includes text blocks, visual assets (images/figures), and metadata, ready for both vector and graph ingestion.

## 5. EVALUATION SYSTEM

The evaluation system provides quantitative metrics for retrieval quality and system latency, integrated with monitoring tools.

### 5.1 Dataset Management
- **dataset_dev.jsonl**: Located in `backend/app/eval/config/`. Contains 20 curated questions with associated ground truth documents and expected answers.
- **Dynamic Generation**: Synthetic queries can be generated using `query_generator.py` to augment the evaluation set using LLM-as-a-judge patterns.

### 5.2 Metrics & Monitoring
- **Recall@K**: Proportion of relevant documents found in top K results. It measures the system's ability to find all relevant documents.
- **MRR (Mean Reciprocal Rank)**: Quality of the ranking for the first relevant result. A higher MRR indicates that relevant documents appear higher in the search results.
- **nDCG (Normalized Discounted Cumulative Gain)**: Measures ranking quality by penalizing relevant results lower in the list, accounting for the position of all relevant documents.
- **Precision@K**: Percentage of retrieved documents that are relevant. It measures the system's ability to exclude irrelevant documents.
- **p95 Latency**: Latency (ms) that 95% of queries complete within. This is a critical performance metric for real-time applications.
- **Monitoring**: Metrics are exported to Prometheus and visualized in Grafana "System Overview" dashboards, providing real-time visibility into system health and performance.

### 5.3 Thresholds
Targets are defined in `backend/app/eval/config/thresholds.yaml` with stage-specific bars:

| Metric | Development Target | Production Target |
|--------|--------------------|-------------------|
| Recall@5 | ≥ 0.60 | ≥ 0.80 |
| MRR | ≥ 0.50 | ≥ 0.75 |
| p95 Latency | ≤ 5000ms | ≤ 2000ms |
| Error Rate | ≤ 1% | ≤ 0.5% |

## 6. CANONICAL COMMANDS

All commands should be run from `backend/` directory with `PYTHONPATH=.`.

### 6.1 Extraction & Migration
- **extract_entities_v2.py**: V2 entity extraction using MiniMax M2.1. Supports test strings and directory batch processing.
  ```bash
  # Test with a specific string
  PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --test "Quercetin inhibits COX-2"
  # Process all documents in a directory
  PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --input-dir data/extractions
  ```
- **migrate_entities_v2.py**: Migrates legacy V1 extractions to the new V2 schema for backward compatibility.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/migrate_entities_v2.py --dir data/extractions
  ```

### 6.2 Ingestion & Management
- **milvus_ingest.py**: Ingests processed blocks and entities into Milvus. Handles collection creation and indexing.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/milvus_ingest.py --input-dir data/extractions
  ```
- **create_id_mapping.py**: Generates `id_mapping.json` (doc_id ↔ file_id) to maintain canonical document references.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/create_id_mapping.py --pdf-dir data/pdfs --ext-dir data/extractions
  ```
- **verify_merge.py**: Checks data integrity of the 129-document corpus, verifying PDF and extraction counts.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/verify_merge.py
  ```
- **aggregate_corpus.py**: Merges extraction metadata into a unified `biblio_corpus.jsonl`.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/aggregate_corpus.py
  ```
- **neo4j_ingest.py**: Graph ingestion logic. **Currently Disabled** as the graph store is not part of the active research stack.

### 6.3 Evaluation & Optimization
- **rag_eval.py**: Runs the evaluation harness against the dev dataset.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/rag_eval.py --top-k 5
  ```
- **rag_optimize.py**: Tunes HNSW parameters (efConstruction, M).
- **API Eval**: `curl -X POST http://localhost:8000/api/v1/eval/run -d '{"dataset_id": "eval-v1"}'`

### 6.4 Utilities & Deprecated
- **recover_extractions.py**: Recovery for failed Marker API extractions. It attempts to resume sessions or re-poll for results that didn't complete successfully.
- **tidy_data.py**: Data cleanup scripts for removing temporary artifacts, normalizing directory structures, and ensuring consistent naming across the extractions.
- **consolidate_archive.py**: Internal utility for merging the `datalab.archive` repository into the LAYRA codebase, preserving history and data artifacts.
- **entity_extract.py**: (Deprecated) Original entity extraction logic used in early stages of the project. Replaced by `extract_entities_v2.py`.
- **entity_extract_gemini.py**: (Deprecated) Experimental script for testing entity extraction using Google's Gemini models.

## 7. INFRASTRUCTURE

| Service | Purpose | Notes |
|---------|---------|-------|
| **MiniMax M2.1** | Entity extraction | Primary LLM; API key in `data/.minimax_api_key` |
| **Milvus** | Vector store | HNSW index (M=48, efConstruction=1024) |
| **Neo4j** | Knowledge graph | **DISABLED** in current research deployment |
| **FastAPI** | Backend API | REST endpoints at `/api/v1/` |

**Configuration**: Managed via `.env` (EMBEDDING_MODEL, MILVUS_HOST, HNSW parameters).

## 8. DATA ARTIFACTS

The `backend/data/` directory contains the core knowledge assets of the system.

- **pdfs/**: 129 source academic papers in PDF format.
- **extractions/**: 129 subdirectories, each containing `entities.json` (V2), `normalized.json` (Blocks), and `images/` (Figures/Tables).
- **id_mapping.json**: Canonical mapping between hash-based `doc_id` and human-readable `file_id`.
- **corpus/**: Contains `biblio_corpus.jsonl` with aggregated document metadata.
- **dataset_dev.jsonl**: 20 curated questions for evaluation ground truth.
- **API Keys**: `.minimax_api_key` and `.datalab_api_key` (Legacy).

These artifacts are essential for maintaining the state of the knowledge base and ensuring reproducible evaluation results across different system configurations.

## 9. HISTORY

| Date | Event |
|------|-------|
| 2026-01-15 | Forked LAYRA, initialized evaluation system |
| 2026-01-20 | Implemented LLM-based relevance labeler for ground truth |
| 2026-01-25 | Integrated p95 latency tracking into evaluation runner |
| 2026-02-01 | Migrated 129 documents to V2 entity format |
| 2026-02-02 | Created entity_extraction module using MiniMax M2.1 |
| 2026-02-02 | Fully merged DataLab into LAYRA repository |
| 2026-02-02 | Consolidated 129 PDFs and extractions into backend/data/ |
| 2026-02-02 | Docker Compose best practices: pinned monitoring images, fixed healthchecks |
| 2026-02-02 | Fixed Prometheus metrics_path, removed Qdrant target |

## 10. CROSS-REFERENCES

- `README.md`: General project overview and setup instructions.
- `backend/lib/entity_extraction/AGENTS.md`: Technical details of the V2 extraction logic.
- `backend/lib/datalab/AGENTS.md`: Detailed documentation for DataLab modules.
- `backend/docs/PIPELINE_AUDIT_2026-02-02.md`: Audit of the current data state.
- `/LAB/@thesis/datalab.archive/`: External backup of the original DataLab project.
