# DataLab Library: Core Processing Logic

Core Python modules for PDF extraction, normalization, and RAG preparation, integrated into LAYRA.

## 1. DIRECTORY STRUCTURE
```text
lib/datalab/
├── datalab_api.py       # API Client (Retries, Backoff, Marker Auth)
├── datalab_ingest.py    # Catalog Manager (SHA256 tracking)
├── datalab_process.py   # Document Runner (Single extraction)
├── datalab_utils.py     # Shared Utilities (Hashing, Sanitization)
├── batch_extractor.py   # CLI Entrypoint (Parallel processing)
├── normalization.py     # Raw -> NormalizedDocumentV2 transformation
├── block_index.py       # Block ID -> bbox/polygon mapping
├── evidence_gate.py     # Confidence-based filtering
├── section_extractor.py # Academic section identification
├── schemas/             # Pydantic data models
│   ├── raw_envelope.py      # RawMarkerEnvelope (API response wrapper)
│   └── normalized_document.py # NormalizedDocumentV2, ImageAsset, FigureRecord
└── repair/              # Metadata Post-processing
    ├── backfill_doi.py  # DOI recovery via CrossRef
    └── backfill_year.py # Publication year recovery
```

## 2. MODULE RESPONSIBILITIES

| Module | Role |
|--------|------|
| `datalab_api` | Marker API client with exponential backoff, polling, result unpacking |
| `datalab_process` | Single document extraction: upload, process, poll, download |
| `datalab_ingest` | Catalog management and document ingestion tracking |
| `datalab_utils` | Shared utilities for hashing, path sanitization, and atomic writes |
| `batch_extractor` | ThreadPoolExecutor for corpus-wide extraction with --mode, --schema |
| `normalization` | Transform RawMarkerEnvelope -> NormalizedDocumentV2 with images/figures |
| `block_index` | Build block_id -> (page_index, bbox, polygon) lookup from Marker JSON |
| `evidence_gate` | Filters extracted entities based on textual evidence confidence scores |
| `section_extractor` | Identifies academic sections (e.g., Introduction, Results, Discussion) |
| `schemas/` | Pydantic models for type safety across the pipeline |
| `repair/` | Scripts for backfilling missing metadata (DOI, Year) |

## 3. NORMALIZATION PIPELINE

`normalize_document(envelope, assets_root)` performs:

1. **Build block_index** from `result.json` (all blocks with geometry)
2. **Parse extraction_schema_json** -> data + citations + anchors
3. **Collect images** from BOTH:
   - Top-level: `result.images` (may be None)
   - Per-block: `result.json.children[N].images` (Marker OSS style)
4. **Persist images** to `_assets/<doc_id>/images/<sha256>.<ext>`
5. **Detect figures** from block_type in {Figure, Picture, Image, PictureGroup}
6. **Match captions** spatially (nearest Caption block below figure)
7. **Enrich chunks** with `graph_meta.anchors`, `image_filenames`, `image_asset_ids`

### Key Functions

| Function | Purpose |
|----------|---------|
| `collect_images_from_json(marker_json)` | Walk JSON tree, collect per-block images |
| `normalize_images_with_persistence(images, dir)` | Decode base64, sha256, write to disk |
| `normalize_figures(doc_id, block_index, filename_map)` | Create FigureRecords with caption matching |
| `normalize_chunks(chunks, doc_id, provenance, block_index)` | Create NormalizedChunks with anchors |

## 4. DATA MODELS (schemas/)

### NormalizedDocumentV2
```python
doc_id: str
metadata: Dict[str, Any]
provenance: ChunkProvenance
block_index: List[BlockIndexEntry]
extraction: Extraction
chunks: List[NormalizedChunk]
images: List[ImageAsset]      # Decoded images with storage_uri
figures: List[FigureRecord]   # Figure blocks with captions
```

### ImageAsset
```python
asset_id: str       # sha256:hex
filename: str       # Original from API
mime: str
byte_size: int
storage_uri: str    # Persisted file path
```

### FigureRecord
```python
figure_id: str          # doc_id/fig/NNNN
block_id: str           # /page/N/Figure/M
page_index: int
bbox: List[float]
polygon: List[List[float]]
caption_text: str
caption_block_id: str
image_asset_id: str     # Links to ImageAsset
```

## 5. CLI USAGE

```bash
# Full extraction with schema
PYTHONPATH=. python3 -m lib.datalab.batch_extractor \
  --mode full \
  --schema data/notes/page_schema_ethnopharmacology.json \
  --output-dir data/PROD_EXTRACTION_V2

# Test mode (6 files)
PYTHONPATH=. python3 -m lib.datalab.batch_extractor --mode test --no-schema

# Chunks-only (RAG optimized, still includes json for anchors)
PYTHONPATH=. python3 -m lib.datalab.batch_extractor --mode full --chunks-only
```

## 6. API PARAMETERS

Correct Marker API request:
```python
output_format="json,html,markdown,chunks"  # html required for images
disable_image_extraction=False
disable_image_captions=False
add_block_ids=True  # Only when html in output_format
```

## 7. CONVENTIONS
- **Hashing**: SHA256 only via `calculate_sha256_file()` or `calculate_sha256_string()`
- **Path Safety**: Always use `sanitize_path_component()` for user input
- **Atomic Writes**: Write to `.tmp`, then `os.replace()` to final path
- **Image Storage**: `_assets/<doc_id>/images/<sha256>.<ext>`
- **Block IDs**: Format `/page/N/BlockType/M` (0-indexed)

## 8. TROUBLESHOOTING

| Issue | Check |
|-------|-------|
| Images = 0 | Verify `html` in output_format; check `collect_images_from_json()` |
| Figures but no captions | Check `find_nearest_caption()` spatial matching |
| Empty block_index | Verify `result.json` exists and is valid JSON |
| Extraction fails | Check `data/logs/` for API errors, rate limits |
