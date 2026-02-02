from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BlockIndexEntry(BaseModel):
    block_id: str
    page_index: Optional[int] = None
    block_type: Optional[str] = None
    bbox: Optional[List[float]] = None
    polygon: Optional[List[List[float]]] = None
    text: Optional[str] = None
    html: Optional[str] = None
    parent_block_id: Optional[str] = None


class Anchor(BaseModel):
    block_id: str
    page_index: Optional[int] = None
    bbox: Optional[List[float]] = None
    polygon: Optional[List[List[float]]] = None


class Extraction(BaseModel):
    data: Dict[str, Any]
    citations: Dict[str, List[str]]
    anchors: Dict[str, List[Anchor]]
    raw_extraction_schema_json: Optional[str] = None
    parse_errors: List[str] = Field(default_factory=list)


class ChunkProvenance(BaseModel):
    source_url: Optional[str] = None
    retrieved_at: datetime
    license: str = "unknown"
    collector_id: str
    ingest_batch: Optional[str] = None


class NormalizedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    html: Optional[str] = None
    page_refs: List[int]
    block_ids: List[str]
    embeddings_meta: Dict[str, Any] = Field(default_factory=dict)
    graph_meta: Optional[Dict[str, Any]] = None
    provenance: ChunkProvenance


class ImageAsset(BaseModel):
    """Decoded image with storage location."""

    asset_id: str  # sha256:hex
    filename: str  # Original filename from API
    mime: str  # image/jpeg, etc.
    byte_size: int
    storage_uri: str  # Path to persisted file


class FigureRecord(BaseModel):
    """Figure block with caption matching."""

    figure_id: str  # doc_id/fig/NNNN
    block_id: str  # /page/N/Figure/M
    page_index: int
    bbox: Optional[List[float]] = None
    polygon: Optional[List[List[float]]] = None
    caption_text: Optional[str] = None
    caption_block_id: Optional[str] = None
    image_asset_id: Optional[str] = None  # Links to ImageAsset


class NormalizedDocumentV2(BaseModel):
    doc_id: str
    metadata: Dict[str, Any]
    provenance: ChunkProvenance
    datalab: Dict[str, Any]
    raw: Dict[str, Any]
    block_index: List[BlockIndexEntry]
    extraction: Extraction
    chunks: List[NormalizedChunk]
    images: List[ImageAsset] = Field(default_factory=list)
    figures: List[FigureRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
