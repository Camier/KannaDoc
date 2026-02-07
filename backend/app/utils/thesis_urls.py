"""Thesis URL helpers.

Thesis deployments may not have Mongo-side file/image metadata. In that case the
backend can still provide stable references via local thesis endpoints.
"""

from __future__ import annotations

from urllib.parse import urlencode


def build_thesis_pdf_url(api_base: str, *, file_id: str) -> str:
    api_base = str(api_base or "").rstrip("/")
    return f"{api_base}/thesis/pdf?" + urlencode({"file_id": str(file_id)})


def build_thesis_page_image_url(
    api_base: str, *, file_id: str, page_number: int, dpi: int = 150
) -> str:
    api_base = str(api_base or "").rstrip("/")
    return f"{api_base}/thesis/page-image?" + urlencode(
        {"file_id": str(file_id), "page_number": int(page_number), "dpi": int(dpi)}
    )

