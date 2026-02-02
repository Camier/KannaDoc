# DataLab RAG Pipeline

RAG-specific logic for chunking, indexing, and retrieval validation.

## Data Flow

```text
[data/extractions/] -> scripts/aggregate_corpus.py -> [data/corpus/]
[data/corpus/]      -> scripts/milvus_ingest.py    -> [Milvus Vector DB]
[Milvus Vector DB]  -> scripts/rag_eval.py         <- [eval/thresholds.yaml]
```

## Scripts Overview

| Script | Input | Output | Role |
|--------|-------|--------|------|
| `aggregate_corpus.py` | Extraction dirs | `corpus/*.jsonl` | Aggregate all extractions into corpus files |
| `milvus_ingest.py` | `chunks.jsonl` | Milvus Collection | Embedding & vector ingestion |
| `neo4j_ingest.py` | Extraction dirs | Neo4j Graph | Document + Entity graph ingestion |
| `rag_eval.py` | `dataset.jsonl` | Metrics/Report | Retrieval quality validation |

## Chunking Strategy

- **Target Size**: 500-1000 characters per chunk (min 50 chars)
- **Logic**: Groups adjacent blocks within the same section hierarchy
- **Metadata**: Chunks retain `doc_id`, `page`, `section`, `year`, and `doi`

## Embedding Configuration

| Parameter | Value |
|-----------|-------|
| Model | `text-embedding-3-large` |
| Dimensions | 3072 |
| Collection | `ethnopharmacology_v2` |
| Batch Size | 100 |

## Milvus Ingestion

```bash
# Ingest normalized documents
python3 scripts/milvus_ingest.py \
  --source normalized \
  --input data/extractions/prod_max

# Ingest aggregated corpus
python3 scripts/milvus_ingest.py \
  --source corpus \
  --input data/corpus/chunks_corpus.jsonl
```

## Neo4j Ingestion

Two-phase ingestion:
1. **Phase 1**: Documents + Chunks (structure)
2. **Phase 2**: Entities (from `entities.json`)

```bash
python3 scripts/neo4j_ingest.py --input data/extractions/prod_max
```

## Evaluation Harness

Custom-built for domain-specific accuracy (Ethnopharmacology).

- **Tool**: `python3 scripts/rag_eval.py`
- **Config**: `eval/thresholds.yaml` defines targets for Dev vs. Prod
- **Metrics**:
  - Recall@k (k=5)
  - MRR (Mean Reciprocal Rank)
  - p95 Latency (target < 2.5s)

```bash
# Run retrieval evaluation
python3 scripts/rag_eval.py --top-k 5
```

## Corpus Statistics (Production)

| Metric | Count |
|--------|-------|
| Documents | 129 |
| Total Chunks | 29,638 |
| Images | 1,565 |
| Avg Chunks/Doc | ~230 |

## Dependencies

- `pymilvus>=2.3.0` (Milvus client)
- `openai` (Embedding generation API)
- `neo4j` (Graph database driver)
- `tqdm` (Progress bars)
