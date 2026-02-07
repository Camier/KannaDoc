# LAYRA (KannaDoc) - Agent Knowledge Base

Academic research fork for thesis work on retrieval evaluation and visual RAG optimization.

## 1. PROJECT OVERVIEW

| Aspect | Details |
|--------|---------|
| **Purpose** | Ethnopharmacology RAG system with evaluation framework |
| **Corpus** | 129 PDFs with V3.1 entities (128 with relationships, 53,800 total) |
| **Status** | DataLab fully merged; V3.1 extraction complete |
| **Stack** | FastAPI + Milvus + DeepSeek (Neo4j disabled) |
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
│   │   │   │   └── knowledge_base.py# KB management (Upload/Delete/List)
│   │   ├── eval/               # Evaluation system
│   │   │   ├── metrics.py      # MRR, NDCG, P@K, R@K implementation
│   │   │   ├── labeler.py      # LLM-based relevance scoring
│   │   │   ├── runner.py       # Orchestration + p95 latency tracking
│   │   │   ├── dataset.py      # Dataset CRUD and persistence
│   │   │   ├── query_generator.py # Synthetic query generation
│   │   │   └── config/
│   │   │       ├── thresholds.yaml    # Quality targets (dev/prod)
│   │   │       └── dataset_dev.jsonl  # 20 curated eval questions
│   │   └── workflow/           # Autonomous workflow engine
│   │       ├── components/     # Checkpoint, LLM, and loop management
│   │       ├── workflow_engine.py# Core orchestration logic
│   │       ├── graph.py        # Graph traversal and nodes
│   │       └── sandbox.py      # Docker-based code execution
│   │
│   ├── lib/
│   │   ├── entity_extraction/  # V3.1 extraction logic
│   │   │   ├── schemas.py      # 17 entity types, 16 relationships
│   │   │   ├── extractor.py    # Zhipu GLM-4.7 + MiniMax fallback
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
│   ├── tests/                  # Comprehensive test suite
│   │   ├── test_rag_pipeline.py# E2E RAG verification
│   │   ├── test_workflow_engine.py# Workflow engine tests
│   │   ├── test_security_utils.py# Security and auth tests
│   │   └── test_eval_metrics.py# Metrics calculation tests
│   │
│   ├── scripts/
│   │   └── datalab/            # Data orchestration scripts
│   │       ├── extract_deepseek.py      # V3.1 extraction CLI (single + batch)
│   │       ├── milvus_ingest.py         # Vector database ingestion
│   │       ├── aggregate_corpus.py      # Aggregating metadata
│   │       ├── create_id_mapping.py     # doc_id ↔ file_id mapping
│   │       ├── rag_eval.py              # CLI evaluation tool
│   │       ├── rag_optimize.py          # HNSW parameter tuning
│   │       ├── verify_merge.py          # Data integrity checks
│   │       ├── recover_extractions.py   # Recovery utilities
│   │       ├── tidy_data.py             # Data cleanup scripts
│   │       └── consolidate_archive.py   # Archive consolidation
│   │
│   └── data/
│       ├── pdfs/               # Source PDFs (dynamic)
│       ├── extractions/        # Extraction results (dynamic)
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

## 3. ENTITY EXTRACTION (V3.1)

**Status**: V3.1 schema is active with 17 entity types and 16 relationships. Extraction uses DeepSeek or Z.ai GLM-4.7.

17 entity types across 6 domains:

| Domain | Types |
|--------|-------|
| Ethnographic | Culture, UseRecord, TraditionalUse, Preparation |
| Botanical | Taxon, PlantPart, RawMaterial |
| Chemical | CompoundClass, Compound |
| Pharmacological | Target, Effect |
| Clinical | Condition, Evidence, Study, Dosage, AdverseEvent |
| Product | Product |

16 relationship types: `HAS_USE`, `INVOLVES`, `HAS_PART`, `TRANSFORMS`, `CONTAINS`, `HAS_CLASS`, `ACTS_ON`, `PRODUCES`, `TREATS`, `SUGGESTS`, `CAUSES`, `INTERACTS_WITH`, `HAS_EVIDENCE`, `STUDIES`, `TESTED_AT`, `REPORTS`.

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
- **extract_deepseek.py**: V3.1 entity extraction CLI pinned to DeepSeek for thesis reproducibility. Supports test strings and directory batch processing.
  ```bash
  # Test with a specific string
  PYTHONPATH=. python3 scripts/datalab/extract_deepseek.py --test "Quercetin inhibits COX-2"
  # Process all documents in a directory
  PYTHONPATH=. python3 scripts/datalab/extract_deepseek.py --input-dir data/extractions
  ```
- **extract_deepseek.py**: (RECOMMENDED) High-throughput async extraction using DeepSeek API.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/extract_deepseek.py --concurrency 20
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
- **verify_merge.py**: Checks data integrity of the corpus, verifying PDF and extraction counts.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/verify_merge.py
  ```
- **aggregate_corpus.py**: Merges extraction metadata into a unified `biblio_corpus.jsonl`.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/aggregate_corpus.py
  ```
- **neo4j_ingest.py**: Graph ingestion logic. **Removed** — graph store not part of active research stack.

### 6.3 Evaluation & Optimization
- **rag_eval.py**: Runs the evaluation harness against the dev dataset.
  ```bash
  PYTHONPATH=. python3 scripts/datalab/rag_eval.py --top-k 5
  ```
- **rag_optimize.py**: Tunes HNSW parameters (efConstruction, M).
- **API Eval**: `curl -X POST http://localhost:8000/api/v1/eval/run -d '{"dataset_id": "eval-v1"}'`

## 7. INFRASTRUCTURE

| Service | Purpose | Notes |
|---------|---------|-------|
| **GLM-4.x (Z.ai)** | Entity extraction | Primary LLM via Z.ai API (`https://api.z.ai/api/paas/v4`); API key: `ZAI_API_KEY` env var |
| MiniMax (Fallback) | Entity extraction fallback | Fallback LLM; API key in `data/.minimax_api_key` |
| **Milvus** | Vector store | HNSW index (M=48, efConstruction=1024); runs on HOST (port 19530) |
| **FastAPI** | Backend API | REST endpoints at `/api/v1/` |

**Configuration**: Managed via `.env` (EMBEDDING_MODEL, MILVUS_URI, HNSW parameters).

### 7.1 Hybrid Search Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_HYBRID_ENABLED` | Enable hybrid search (dense + sparse) | `false` |
| `RAG_HYBRID_RANKER` | Ranking strategy (`rrf` or `weighted`) | `rrf` |
| `RAG_HYBRID_RRF_K` | RRF smoothing constant (default: 60) | `60` |
| `RAG_HYBRID_DENSE_WEIGHT` | Weight for dense retrieval (if ranker=weighted) | `0.7` |
| `RAG_HYBRID_SPARSE_WEIGHT` | Weight for sparse retrieval (if ranker=weighted) | `0.3` |


## 8. DATA ARTIFACTS

The `backend/data/` directory contains the core knowledge assets of the system.

- **pdfs/**: Source academic papers in PDF format (dynamic).
- **extractions/**: Document subdirectories, each containing `entities.json` (V2), `normalized.json` (Blocks), and `images/` (Figures/Tables).
- **id_mapping.json**: Canonical mapping between hash-based `doc_id` and human-readable `file_id`.
- **corpus/**: Contains `biblio_corpus.jsonl` with aggregated document metadata.
- **dataset_dev.jsonl**: 20 curated questions for evaluation ground truth.
- **API Keys**: `ZAI_API_KEY` (environment variable for Zhipu), `.minimax_api_key` (fallback), and `.datalab_api_key` (Legacy).

These artifacts are essential for maintaining the state of the knowledge base and ensuring reproducible evaluation results across different system configurations.

## 9. HISTORY

| Date | Event |
|------|-------|
| 2026-01-15 | Forked LAYRA, initialized evaluation system |
| 2026-01-20 | Implemented LLM-based relevance labeler for ground truth |
| 2026-01-25 | Integrated p95 latency tracking into evaluation runner |
| 2026-02-01 | Migrated 129 documents to V2 entity format |
| 2026-02-02 | Created entity_extraction module using Zhipu GLM-4.7 |
| 2026-02-02 | Fully merged DataLab into LAYRA repository |
| 2026-02-02 | Consolidated 129 PDFs and extractions into backend/data/ |
| 2026-02-02 | Docker Compose best practices: pinned monitoring images, fixed healthchecks |
| 2026-02-02 | Fixed Prometheus metrics_path, removed Qdrant target |
| 2026-02-07 | Audit hardening: stack traces, dead code cleanup, Qdrant refs removed |
| 2026-02-07 | Fixed KB upload pipeline (frontend path + Kafka trigger) |
| 2026-02-07 | Wired eval dashboard to real backend API |
| 2026-02-07 | Applied circuit breakers to DB calls, fixed async blocking I/O |
| 2026-02-07 | Removed deprecated scripts (configure_models.py, _archived/, neo4j_ingest.py) |

## 10. CROSS-REFERENCES

- `README.md`: General project overview and setup instructions.
- `backend/lib/entity_extraction/AGENTS.md`: Technical details of the V2 extraction logic.
- `backend/lib/datalab/AGENTS.md`: Detailed documentation for DataLab modules.
- `backend/docs/PIPELINE_AUDIT_2026-02-02.md`: Audit of the current data state.
- `/LAB/@thesis/datalab.archive/`: External backup of the original DataLab project.

## 11. WORKFLOW ENGINE

The system includes an autonomous workflow orchestration engine located in `backend/app/workflow/`. It enables complex multi-step reasoning and tool-augmented execution.

### 11.1 Key Components
- **WorkflowEngine**: Central orchestrator managing state, graph traversal, and execution flow.
- **CodeSandbox**: Docker-based execution environment for safe Python code evaluation.
- **Graph & TreeNode**: Recursive data structures for modeling complex workflow DAGs.
- **WorkflowCheckpointManager**: Redis-backed state persistence for fault tolerance and recovery.
- **MCP Tool Bridge**: Integration layer for Model Context Protocol (MCP) tool invocation.

### 11.2 Capabilities
- **Stateful Execution**: Context sharing across nodes with loop and recursion limits.
- **Sandboxed Execution**: Isolated environments for dynamically generated code.
- **LLM Fault Tolerance**: Circuit breakers and exponential backoff for LLM provider calls.

## 12. TEST SUITE

The repository maintains a comprehensive test suite using `pytest`. Tests are located in `backend/tests/` and cover unit, functional, and integration levels.

### 12.1 Key Test Modules
- `test_rag_pipeline.py`: End-to-end RAG workflow verification including retrieval and generation.
- `test_workflow_engine.py`: Tests for the autonomous workflow orchestration engine.
- `test_eval_metrics.py`: Verification of IR metrics (MRR, NDCG, etc.) calculation logic.
- `test_hybrid_search.py`: Tests for multi-vector and filtered search capabilities.
- `test_security_utils.py`: Security-critical tests for hashing, encryption, and data sanitization.
- `test_repositories_crud.py`: CRUD operation tests for the database repository layer.
- `test_performance.py`: Latency and throughput benchmarks for critical paths.

### 12.2 Execution
All tests should be run from the `backend/` directory.

```bash
# Run all tests
PYTHONPATH=. pytest tests/

# Run specific test file
PYTHONPATH=. pytest tests/test_rag_pipeline.py
```

### 12.3 Coverage Areas
- **RAG & Search**: Retrieval precision, HNSW parameter tuning, and hybrid ranking.
- **Workflows**: Graph traversal integrity and sandbox isolation.
- **Security**: Password migration, token validation, and API rate limiting.
