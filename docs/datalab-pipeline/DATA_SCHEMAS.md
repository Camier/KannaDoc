# DataLab Data Schemas

Pydantic models and JSON structures used in the DataLab extraction pipeline.

## NormalizedDocumentV2

The primary output format for processed documents.

```python
class NormalizedDocumentV2:
    doc_id: str                        # SHA256 hash of source filename
    metadata: Dict[str, Any]           # Extracted fields (title, authors, compounds, plants, effects)
    provenance: ChunkProvenance        # Source file info
    block_index: List[BlockIndexEntry] # All blocks with bbox/polygon
    extraction: Extraction             # Structured data + citations + anchors
    chunks: List[NormalizedChunk]      # RAG-ready text chunks
    images: List[ImageAsset]           # Decoded images with storage_uri
    figures: List[FigureRecord]        # Figure blocks with caption matching
```

## ImageAsset

Represents a decoded and persisted image.

```python
class ImageAsset:
    asset_id: str      # sha256:hex
    filename: str      # Original filename from API
    mime: str          # image/jpeg, image/png, etc.
    byte_size: int     # File size in bytes
    storage_uri: str   # Path to persisted file
```

## FigureRecord

Links figure blocks to their captions and image assets.

```python
class FigureRecord:
    figure_id: str         # doc_id/fig/NNNN
    block_id: str          # /page/N/Figure/M
    page_index: int        # 0-indexed page number
    bbox: List[float]      # [x0, y0, x1, y1] bounding box
    polygon: List[List[float]]  # Precise boundary points
    caption_text: str      # Matched caption text
    caption_block_id: str  # Block ID of caption
    image_asset_id: str    # Links to ImageAsset.asset_id
```

## NormalizedChunk

RAG-ready text chunk with metadata.

```python
class NormalizedChunk:
    id: str                # chunk_<index>
    text: str              # Chunk content
    html: Optional[str]    # HTML version if available
    page: int              # Source page number
    section: Optional[str] # Section hierarchy
    graph_meta: GraphMeta  # Anchors, image references
```

## BlockIndexEntry

Maps block IDs to their geometry.

```python
class BlockIndexEntry:
    block_id: str              # /page/N/BlockType/M
    page_index: int            # 0-indexed page
    bbox: List[float]          # [x0, y0, x1, y1]
    polygon: List[List[float]] # Precise boundary
    block_type: str            # Text, Figure, Table, etc.
```

## Entities Output (entities.json)

Output from Gemini NER extraction.

```python
{
    "doc_id": str,           # SHA256 hash
    "chunk_entities": [
        {
            "chunk_id": str,
            "entities": [
                {
                    "entity_type": str,   # Compound, Plant, Effect, Disease, Dosage
                    "entity_name": str,
                    "context": str        # Brief surrounding context
                }
            ]
        }
    ],
    "total_entities": int,
    "extraction_date": str,  # ISO 8601 timestamp
    "status": str,           # "complete" or "partial"
    "model": str,            # e.g., "gemini-2.5-flash"
    "processed_chunks": int,
    "total_chunks": int
}
```

## ID Mapping (id_mapping.json)

Links DataLab doc_id to LAYRA file_id.

```python
[
    {
        "filename": str,       # Original PDF filename
        "doc_id": str,         # SHA256 hash (DataLab identifier)
        "file_id": str,        # LAYRA file identifier (stem of filename)
        "datalab_path": str,   # Full path to source PDF
        "layra_exists": bool   # Whether file exists in LAYRA corpus
    }
]
```

## Corpus Files

### biblio_corpus.jsonl

One JSON object per line, bibliographic metadata:

```python
{
    "doc_id": str,
    "paper_id": str,        # Extracted paper identifier
    "title": str,
    "authors": List[str],
    "year": Optional[int],
    "doi": Optional[str],
    "abstract": Optional[str]
}
```

### chunks_corpus.jsonl

One JSON object per line, RAG chunks:

```python
{
    "doc_id": str,
    "chunk_id": str,
    "text": str,
    "page": int,
    "section": Optional[str],
    "char_count": int
}
```

### images_manifest.json

Image asset catalog:

```python
{
    "total_images": int,
    "images": [
        {
            "doc_id": str,
            "asset_id": str,
            "filename": str,
            "storage_uri": str,
            "byte_size": int,
            "mime": str
        }
    ]
}
```
