# Entity Extraction (Gemini NER)

Parallel entity extraction using Gemini 2.5 Flash via CLIProxyAPI.

## Overview

Extracts domain-specific entities from ethnopharmacology literature:
- **Compound**: Chemical compounds, alkaloids, molecules
- **Plant**: Plant species (scientific and common names)
- **Effect**: Pharmacological effects (anti-inflammatory, anxiolytic, etc.)
- **Disease**: Medical conditions or diseases
- **Dosage**: Dosage information with amounts and units

## Script Location

```
/LAB/@thesis/datalab/scripts/entity_extract_gemini.py
```

## Usage

```bash
# Full extraction (parallel)
python3 scripts/entity_extract_gemini.py \
  --input-dir data/extractions/prod_max \
  --doc-workers 12 \
  --chunk-workers 4

# Test mode
python3 scripts/entity_extract_gemini.py \
  --test "Mesembrine from Sceletium tortuosum shows anxiolytic effects"

# Limited run
python3 scripts/entity_extract_gemini.py \
  --input-dir data/extractions/prod_max \
  --limit 10
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-dir` | `data/extractions/prod_max/` | Base extraction directory |
| `--doc-workers` | 8 | Concurrent documents to process |
| `--chunk-workers` | 4 | Parallel workers per document |
| `--model` | `gemini-2.5-flash` | Model name |
| `--limit` | None | Limit number of documents |
| `--test` | None | Test extraction on provided text |
| `--min-request-interval` | 1.5 | Seconds between API requests |

## Infrastructure

| Component | Value |
|-----------|-------|
| API Endpoint | `http://localhost:8317/v1` |
| API Key | `layra-cliproxyapi-key` |
| Model | `gemini-2.5-flash` |
| Rate Limit | 1.5s between requests (per worker) |

## Output Format

Each document gets an `entities.json` file:

```json
{
  "doc_id": "6d49903670e540f3...",
  "chunk_entities": [
    {
      "chunk_id": "069d028e6ed9ca41...",
      "entities": [
        {
          "entity_type": "Compound",
          "entity_name": "Mesembrine",
          "context": "Mesembrine is the primary alkaloid..."
        },
        {
          "entity_type": "Plant",
          "entity_name": "Sceletium tortuosum",
          "context": "...from Sceletium tortuosum (Kanna)"
        }
      ]
    }
  ],
  "total_entities": 42,
  "extraction_date": "2026-02-01T23:27:40.857Z",
  "status": "complete",
  "model": "gemini-2.5-flash",
  "processed_chunks": 230,
  "total_chunks": 230
}
```

## Parallelization Strategy

Two-level parallelization:
1. **Document Level**: `--doc-workers` concurrent documents
2. **Chunk Level**: `--chunk-workers` concurrent chunks per document

Recommended configuration:
- `--doc-workers 12`: High concurrency for documents
- `--chunk-workers 4`: Moderate concurrency within each document

## Resume Capability

The script supports resume:
- Checks for existing `entities.json` with `status: "complete"` → skips
- Checks for `status: "partial"` → resumes from last checkpoint
- Checkpoints every 25 chunks

## Performance

| Metric | Sequential | Parallel (12 workers) |
|--------|------------|----------------------|
| 129 docs | ~15-20 hours | ~1-2 hours |
| Throughput | ~6 docs/hour | ~65+ docs/hour |

## Verification

```bash
# Count completed extractions
ls data/extractions/prod_max/*/entities.json | wc -l

# Check a sample
python3 -c "
import json
from pathlib import Path
sample = next(Path('data/extractions/prod_max').iterdir())
entities = json.load(open(sample / 'entities.json'))
print(f'Doc: {entities[\"doc_id\"][:16]}...')
print(f'Entities: {entities[\"total_entities\"]}')
print(f'Status: {entities[\"status\"]}')
"
```
