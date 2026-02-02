# DATALAB SCRIPTS

Documentation for the processing and ingestion pipeline scripts located in `backend/scripts/datalab/`. These scripts handle the transformation of raw PDF extractions into searchable knowledge.

## 1. OVERVIEW

The scripts are categorized into three groups:
- **ACTIVE**: Core pipeline scripts for extraction, ingestion, and evaluation.
- **UTILITY**: Maintenance, verification, and data organization tools.
- **DEPRECATED**: Legacy scripts replaced by newer versions.

| Script | Category | Purpose |
|--------|----------|---------|
| `extract_entities_v2.py` | ACTIVE | V2 entity extraction using MiniMax M2.1 |
| `migrate_entities_v2.py` | ACTIVE | Migrate V1 entities to V2 format |
| `milvus_ingest.py` | ACTIVE | Ingest vectors to Milvus |
| `neo4j_ingest.py` | ACTIVE | Ingest entities into Neo4j (disabled) |
| `rag_eval.py` | ACTIVE | RAG evaluation harness with metrics |
| `rag_optimize.py` | ACTIVE | Semantic chunking and optimization |
| `aggregate_corpus.py` | UTILITY | Aggregate corpus into JSONL manifests |
| `create_id_mapping.py` | UTILITY | Generate doc_id ↔ file_id mapping |
| `verify_merge.py` | UTILITY | Verify DataLab to LAYRA merge |
| `recover_extractions.py` | UTILITY | Recovery tools for Marker API |
| `tidy_data.py` | UTILITY | Data cleanup and organization |
| `consolidate_archive.py` | UTILITY | Archive consolidation tool |
| `entity_extract.py` | DEPRECATED | Old extraction (replaced by v2) |
| `entity_extract_gemini.py` | DEPRECATED | Gemini extraction (replaced by v2) |

---

## 2. ACTIVE SCRIPTS

### extract_entities_v2.py

**Purpose**: Extracts ethnopharmacological entities using the MiniMax M2.1 model according to the V2 schema (15 entity types).

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py [options]
```

**Arguments**:
- `--input-dir`: Directory containing document folders with `normalized.json`.
- `--output-dir`: Output directory (default: same as input).
- `--test`: Test extraction on provided string.
- `--lightning`: Use `MiniMax-M2.1-lightning` for faster processing.
- `--force`: Overwrite existing `entities.json`.
- `--doc-workers`: Number of parallel document workers (default: 4).

**Example**:
```bash
# Test extraction
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --test "Quercetin inhibits COX-2"

# Process all extractions
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --input-dir data/extractions --lightning
```

---

### migrate_entities_v2.py

**Purpose**: Migrates legacy `entities.json` files from the V1 format to the new V2 schema.

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/migrate_entities_v2.py --input-dir data/extractions [options]
```

**Arguments**:
- `--input-dir`: (Required) Directory containing document subdirectories.
- `--dry-run`: Show what would be migrated without writing.
- `--force`: Overwrite even if V2 format is detected.

---

### milvus_ingest.py

**Purpose**: Ingests RAG-optimized chunks or normalized text blocks into the Milvus vector database.

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/milvus_ingest.py [options] <chunks_file>
```

**Arguments**:
- `<chunks_file>`: Path to JSONL file (rag_chunks) or directory (normalized).
- `--collection`: Milvus collection name (default: `ethnopharmacology_v2`).
- `--source`: `{rag_chunks,normalized}` - Source format (default: `rag_chunks`).
- `--ollama`: Use Ollama local embeddings instead of OpenAI.
- `--batch-size`: Number of chunks per batch (default: 100).

**Example**:
```bash
# Ingest optimized chunks
PYTHONPATH=. python3 scripts/datalab/milvus_ingest.py data/rag/all_chunks.jsonl

# Ingest directly from normalized extractions
PYTHONPATH=. python3 scripts/datalab/milvus_ingest.py data/extractions --source normalized
```

---

### neo4j_ingest.py

**Purpose**: Ingests entities and relationships into Neo4j graph database. Note: Neo4j is currently disabled in the main research deployment.

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/neo4j_ingest.py [options]
```

**Arguments**:
- `--doc-dir`: Path to document directory with `normalized.json`.
- `--test-connection`: Test connection and exit.
- `--create-constraints`: Create database constraints and exit.

---

### rag_eval.py

**Purpose**: Runs the RAG evaluation harness against a curated dataset to compute IR metrics (MRR, NDCG, Recall@K).

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/rag_eval.py [options]
```

**Arguments**:
- `--dataset`: Path to evaluation set JSONL (default: `app/eval/config/dataset_dev.jsonl`).
- `--top-k`: Number of documents to retrieve (default: 5).
- `--thresholds`: Path to thresholds YAML file.

**Example**:
```bash
PYTHONPATH=. python3 scripts/datalab/rag_eval.py --top-k 10 --dataset data/eval/test_set.jsonl
```

---

### rag_optimize.py

**Purpose**: Transforms DataLab extraction output (`normalized.json`) into RAG-ready chunks with semantic boundaries and metadata.

**Usage**:
```bash
PYTHONPATH=. python3 scripts/datalab/rag_optimize.py [options] <extraction_path>
```

**Arguments**:
- `<extraction_path>`: Path to a single extraction or parent directory (with `--batch`).
- `--batch`: Process all subdirectories and aggregate.
- `--output`: Output file path for aggregated chunks.

**Example**:
```bash
# Optimize all documents in a directory
PYTHONPATH=. python3 scripts/datalab/rag_optimize.py data/extractions --batch --output data/rag/all_chunks.jsonl
```

---

## 3. UTILITY SCRIPTS

| Script | Purpose | Notes |
|--------|---------|-------|
| `aggregate_corpus.py` | Merges extraction metadata and blocks into aggregated JSONL manifests. | Uses `data/cache/metadata/paper_catalog.jsonl` as source. |
| `create_id_mapping.py` | Generates `id_mapping.json` by matching DataLab PDFs with LAYRA extractions. | **Hardcoded paths**: Expects `/LAB/@thesis/datalab/ALL_FLAT`. |
| `verify_merge.py` | Validates that all documents in `id_mapping.json` have corresponding extraction directories. | Ensures data integrity of the 129-doc corpus. |
| `recover_extractions.py` | Powerful CLI to recover failed extractions from Marker API logs or re-download results. | Requires `.datalab_api_key`. |
| `tidy_data.py` | Organizes the `data/` directory by moving files to `config/`, `cache/`, or `_archive/`. | High-level cleanup tool. |
| `consolidate_archive.py` | Moves old extractions and test data to a structured archive with manifests. | Useful for managing storage and clutter. |

---

## 4. DEPRECATED SCRIPTS

> [!WARNING]
> These scripts are preserved for historical reference but should not be used for production data.

- **`entity_extract.py`**: Original V1 extraction using GPT-4o-mini. Replaced by `extract_entities_v2.py` which supports the 15-type ontology and MiniMax M2.1.
- **`entity_extract_gemini.py`**: Experimental Gemini 1.5/2.0 extraction script. Functionality merged into the V2 extraction framework.

---

## 5. COMMON PATTERNS

### Running Scripts
All scripts should be run from the `backend/` directory with `PYTHONPATH` set to the current directory:
```bash
cd backend
PYTHONPATH=. python3 scripts/datalab/script_name.py [args]
```

### Path Conventions
Many utility scripts use hardcoded absolute paths starting with `/LAB/@thesis/`. If moving the project, these scripts may require updates or path redirection.

### Credentials
- MiniMax API: `backend/data/.minimax_api_key`
- DataLab (Marker) API: `backend/data/.datalab_api_key`
- Milvus/Neo4j: Configuration via `.env` in `backend/`.
