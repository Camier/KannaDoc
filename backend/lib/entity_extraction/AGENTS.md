# Entity Extraction Module

Unified entity extraction using MiniMax M2.1 API with 15-type ontology for ethnopharmacology RAG.

## 1. MODULE STRUCTURE

```text
lib/entity_extraction/
├── __init__.py      # Public API exports
├── schemas.py       # Pydantic models (Entity, Relationship, ExtractionResultV2)
├── prompt.py        # EXTRACTION_PROMPT template + build_prompt()
└── extractor.py     # MinimaxExtractor class
```

## 2. QUICK START

```python
from lib.entity_extraction import MinimaxExtractor

extractor = MinimaxExtractor()  # Reads key from data/.minimax_api_key
result = extractor.extract_chunk("Quercetin inhibits COX-2", doc_id="test")
print(result.entities)
```

## 3. ENTITY TYPES (15)

### Ethnographic Domain
- **Culture**: Ethnic groups, indigenous communities
- **TraditionalUse**: Traditional medicinal applications
- **Preparation**: Methods of preparing plant material

### Botanical Domain
- **Taxon**: Species, genus, or family names
- **PlantPart**: Specific plant parts (roots, leaves, bark)
- **RawMaterial**: Processed plant material (extracts)

### Chemical Domain
- **CompoundClass**: Chemical categories (alkaloids, flavonoids)
- **Compound**: Specific molecules (quercetin, curcumin)
- **Concentration**: Quantitative amounts (IC50, percentages)

### Pharmacological Domain
- **Target**: Biological targets (receptors, enzymes)
- **Mechanism**: Molecular mechanisms (inhibition, agonism)
- **PharmEffect**: Pharmacological effects (anxiolytic, anti-inflammatory)

### Clinical Domain
- **Indication**: Diseases or conditions
- **Evidence**: Study evidence type (clinical trial, in vitro)
- **Study**: Study metadata (sample size, design)

## 4. RELATIONSHIP TYPES (6)

| Type | Direction | Description |
|------|-----------|-------------|
| `TRANSFORMS` | Preparation → RawMaterial | How preparation creates material |
| `CONTAINS` | Taxon/PlantPart → Compound | What contains what |
| `ACTS_ON` | Compound → Target | Molecular interactions |
| `PRODUCES` | Mechanism → PharmEffect | How mechanisms lead to effects |
| `TREATS` | PharmEffect → Indication | Therapeutic relationships |
| `SUGGESTS` | Evidence → Indication | Evidence supporting use |

## 5. API CONFIGURATION

Based on [MiniMax official docs](https://platform.minimax.io/docs/):

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `temperature` | 1.0 | Required for M2.1 reasoning models |
| `top_p` | 0.95 | Recommended for reasoning |
| `max_completion_tokens` | 4096 | Prevent truncation |
| `reasoning_split` | true | Separate `<think>` from output |
| `timeout` | 120s | Handle complex extractions |

### Model Variants

| Model | Speed | Use Case |
|-------|-------|----------|
| `MiniMax-M2.1` | ~60 tps | Default, best accuracy |
| `MiniMax-M2.1-lightning` | ~100 tps | High-volume, `--lightning` flag |

## 6. CLI USAGE

```bash
cd /LAB/@thesis/layra/backend

# Test extraction
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --test "Curcumin inhibits COX-2"

# Full corpus extraction
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py \
  --input-dir data/extractions \
  --doc-workers 4 \
  --chunk-workers 2

# Lightning mode (67% faster)
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --lightning --input-dir data/extractions

# Dry run
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --input-dir data/extractions --dry-run

# Migrate V1 to V2
PYTHONPATH=. python3 scripts/datalab/migrate_entities_v2.py --input-dir data/extractions --dry-run
```

## 7. OUTPUT FORMAT (ExtractionResultV2)

```json
{
  "schema_version": "2.0",
  "doc_id": "abc123",
  "extracted_at": "2026-02-02T08:00:00Z",
  "extractor": "minimax:MiniMax-M2.1",
  "entities": [
    {
      "id": "ent_001",
      "type": "Compound",
      "name": "quercetin",
      "attributes": {"compound_class": "flavonoid"},
      "source_chunk_ids": ["chunk_001"]
    }
  ],
  "relationships": [
    {
      "id": "rel_001",
      "type": "CONTAINS",
      "source_entity_id": "ent_002",
      "target_entity_id": "ent_001",
      "attributes": {}
    }
  ],
  "metadata": {"chunks_processed": 20}
}
```

## 8. ROBUSTNESS FEATURES

- **Retry with backoff**: 3 attempts with 1s, 2s, 4s delays
- **`<think>` stripping**: Removes reasoning blocks before JSON parse
- **Multi-strategy JSON parsing**: Direct → markdown block → greedy `{...}`
- **Truncation safety**: Chunks > 8000 chars truncated with marker

## 9. API KEY SETUP

```bash
# Option 1: File
echo "your-minimax-api-key" > data/.minimax_api_key

# Option 2: Environment variable
export MINIMAX_API_KEY="your-minimax-api-key"
```

## 10. DEPRECATION

The following scripts are deprecated (kept for reference in `scripts/datalab/`):
- `entity_extract.py` → Use `extract_entities_v2.py`
- `entity_extract_gemini.py` → Use `extract_entities_v2.py`

Running deprecated scripts will emit `DeprecationWarning`.

## 11. CROSS-REFERENCES

- `/LAB/@thesis/layra/README.md`: Project overview
- `/LAB/@thesis/layra/backend/scripts/datalab/`: Ingestion scripts
- [MiniMax API Docs](https://platform.minimax.io/docs/api-reference/text-openai-api): OpenAI-compatible API
- [MiniMax Best Practices](https://platform.minimax.io/docs/coding-plan/best-practices): M2.1 usage tips

## 12. HISTORY

- **2026-02-02**: Module created in DataLab, copied to LAYRA
- **2026-02-02**: DataLab archived → `/LAB/@thesis/datalab.archive`
- Assets consolidated into LAYRA (`backend/lib/datalab/`, `backend/data/pdfs/`)
