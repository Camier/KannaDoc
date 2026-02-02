from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DatalabOptions(BaseModel):
    output_format: str = "json,chunks,html"
    mode: str = "balanced"
    page_range: Optional[str] = None
    add_block_ids: bool = True
    page_schema: Optional[str] = None


class DatalabMetadata(BaseModel):
    request_id: str
    request_check_url: Optional[str] = None
    options: DatalabOptions


class Provenance(BaseModel):
    source_file: str
    sha256: str
    retrieved_at: datetime
    collector_id: str = "datalab_pipeline_v2"
    ingest_batch: Optional[str] = None


class RawMarkerEnvelope(BaseModel):
    """Store raw Datalab response for audit/replay."""

    doc_id: str
    datalab: DatalabMetadata
    raw_result: Dict[str, Any]
    provenance: Provenance

    model_config = ConfigDict(extra="forbid")
