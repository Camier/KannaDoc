"""
Thesis-specific debug/utility endpoints.

These endpoints exist to support thesis RAG debugging when Mongo/MinIO metadata is
missing or not aligned with Milvus `file_id` values (which can be human-readable
titles). They do not modify Milvus and do not touch vector data.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.core.logging import logger

router = APIRouter()


def _default_thesis_pdf_dir() -> Path:
    # layra/backend/app/api/endpoints/thesis.py -> layra/backend/data/pdfs
    # parents[3] points to ".../backend"
    return Path(__file__).resolve().parents[3] / "data" / "pdfs"


def _resolve_pdf_path(file_id: str) -> Path:
    """Resolve a thesis PDF path from a `file_id` (expected to match the PDF stem)."""
    if not file_id:
        raise HTTPException(status_code=400, detail="file_id is required")
    if any(sep in file_id for sep in ("/", "\\", "\x00")) or ".." in file_id:
        raise HTTPException(status_code=400, detail="Invalid file_id")

    pdf_dir = _default_thesis_pdf_dir()
    if not pdf_dir.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Thesis PDF directory not found: {str(pdf_dir)}",
        )

    candidate_names: list[str] = []
    if file_id.lower().endswith(".pdf"):
        candidate_names.append(file_id)
    candidate_names.append(f"{file_id}.pdf")
    candidate_names.append(f"{file_id}.PDF")

    for name in candidate_names:
        p = pdf_dir / name
        if p.exists() and p.is_file():
            return p

    for p in pdf_dir.glob("*.pdf"):
        if p.stem == file_id:
            return p
    for p in pdf_dir.glob("*.PDF"):
        if p.stem == file_id:
            return p

    raise HTTPException(status_code=404, detail=f"PDF not found for file_id={file_id}")


@router.get("/pdf")
def get_thesis_pdf(file_id: str = Query(..., description="Thesis file_id (PDF stem).")):
    """Serve a thesis PDF by file_id from `backend/data/pdfs/`."""
    pdf_path = _resolve_pdf_path(file_id)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/page-image")
def get_thesis_page_image(
    file_id: str = Query(..., description="Thesis file_id (PDF stem)."),
    page_number: int = Query(..., ge=1, description="1-based PDF page number."),
    dpi: int = Query(150, ge=72, le=300, description="Render DPI (bounded)."),
):
    """Render a single PDF page as an image for preview/debug UIs."""
    # Lazy import: avoids hard dependency in unit-only environments.
    try:
        from pdf2image import convert_from_path
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"pdf2image is unavailable: {e}")

    pdf_path = _resolve_pdf_path(file_id)

    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=int(dpi),
            first_page=int(page_number),
            last_page=int(page_number),
            fmt="png",
            thread_count=1,
        )
    except Exception as e:
        logger.warning(
            "Failed to render thesis page image (file_id=%s page=%s): %s",
            file_id,
            page_number,
            e,
        )
        raise HTTPException(status_code=500, detail="Failed to render PDF page image")

    if not images:
        raise HTTPException(status_code=404, detail="Page not found in PDF")

    buf = io.BytesIO()
    images[0].save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )
