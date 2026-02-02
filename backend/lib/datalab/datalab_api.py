#!/usr/bin/env python3
"""
Shared Datalab Marker API client with file_url support and retry logic.
Used by both enhanced pipeline and legacy datalab_process.
"""

import base64
import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import requests
import mimetypes

from .datalab_utils import sanitize_path_component


# -----------------------------
# Defaults (aligned with Marker API)
# -----------------------------
DEFAULT_MODE = "accurate"  # highest accuracy for scientific PDFs
DEFAULT_OUTPUT_FORMAT = "json,markdown,chunks"  # chunks for RAG
DEFAULT_PAGINATE = True  # add page delimiters
DEFAULT_ADD_BLOCK_IDS = True  # citation tracking
DEFAULT_DISABLE_IMAGE_EXTRACTION = False
DEFAULT_DISABLE_IMAGE_CAPTIONS = False
DEFAULT_EXTRAS = "extract_links,chart_understanding,table_row_bboxes"  # RAG-optimized

DEFAULT_SUBMIT_TIMEOUT_S = 300
DEFAULT_POLL_MAX_WAIT_S = 45 * 60
DEFAULT_POLL_INTERVAL_S = 5

DEFAULT_MAX_SUBMIT_RETRIES = 3
DEFAULT_MAX_POLL_RETRIES = 5
DEFAULT_MAX_RATE_LIMIT_DELAY = 60


# -----------------------------
# Data classes
# -----------------------------
@dataclass
class MarkerOptions:
    mode: str
    output_format: str
    paginate: bool
    add_block_ids: bool
    disable_image_extraction: bool
    disable_image_captions: bool
    extras: str
    segmentation_schema_json: Optional[str]
    additional_config_json: Optional[str]
    force_ocr: bool = False


# -----------------------------
# Helpers
# -----------------------------
def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def bool_str(v: bool) -> str:
    return "true" if v else "false"


def load_api_key(root: Optional[Path] = None) -> str:
    """
    Load API key from environment variable DATALAB_API_KEY.
    If not found and root is provided, try reading from root/data/.datalab_api_key.
    """
    api_key = os.environ.get("DATALAB_API_KEY", "").strip()
    if api_key:
        return api_key

    if root is not None:
        api_key_file = root / "data" / ".datalab_api_key"
        if api_key_file.exists():
            api_key = api_key_file.read_text(encoding="utf-8").strip()
            if api_key:
                logging.debug("Loading API key from file location")
                return api_key

    raise RuntimeError(
        "Missing API key. Set DATALAB_API_KEY or create data/.datalab_api_key"
    )


# -----------------------------
# Retry wrappers
# -----------------------------
def post_with_retries(
    url: str,
    headers: dict,
    data: dict,
    files: Optional[dict],
    timeout_s: int,
    logger: logging.Logger,
) -> requests.Response:
    """
    Submit request with retries for rate limiting (429) and transient errors.
    If files is None, treat as file_url request (no multipart).
    """
    last_exc = None
    for attempt in range(1, DEFAULT_MAX_SUBMIT_RETRIES + 1):
        try:
            if files is not None:
                r = requests.post(
                    url, headers=headers, data=data, files=files, timeout=timeout_s
                )
            else:
                r = requests.post(url, headers=headers, data=data, timeout=timeout_s)

            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                if ra and ra.isdigit():
                    sleep_s = min(DEFAULT_MAX_RATE_LIMIT_DELAY, int(ra))
                else:
                    sleep_s = min(
                        DEFAULT_MAX_RATE_LIMIT_DELAY, 5 * (2 ** (attempt - 1))
                    )
                sleep_s += random.uniform(0, 1.5)
                logger.warning(
                    f"429 rate limited. Sleeping {sleep_s:.1f}s (attempt {attempt})."
                )
                time.sleep(sleep_s)
                continue

            if r.status_code == 400:
                error_body = r.text[:500]
                logger.error(f"400 Bad Request. Response: {error_body}")
                raise requests.HTTPError(f"400 Bad Request: {error_body}", response=r)

            r.raise_for_status()
            return r

        except (
            requests.RequestException,
            requests.Timeout,
            requests.ConnectionError,
        ) as e:
            if isinstance(e, requests.HTTPError) and e.response is not None:
                if 400 <= e.response.status_code < 500:
                    raise

            last_exc = e
            sleep_s = min(30, 2**attempt + random.random())
            logger.warning(
                f"Submit failed (attempt {attempt}): {e}. Sleeping {sleep_s:.1f}s."
            )
            time.sleep(sleep_s)

    raise RuntimeError(f"Submit failed after retries: {last_exc}")


def post_file_with_retries(
    url: str,
    headers: dict,
    data: dict,
    file_path: Path,
    timeout_s: int,
    logger: logging.Logger,
) -> requests.Response:
    """
    Submit file upload with retries, reopening the file on each attempt.
    """
    last_exc = None
    for attempt in range(1, DEFAULT_MAX_SUBMIT_RETRIES + 1):
        try:
            with file_path.open("rb") as f:
                files = {"file": (file_path.name, f, "application/pdf")}
                r = requests.post(
                    url, headers=headers, data=data, files=files, timeout=timeout_s
                )

            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                sleep_s = (
                    min(DEFAULT_MAX_RATE_LIMIT_DELAY, int(ra))
                    if (ra and ra.isdigit())
                    else min(DEFAULT_MAX_RATE_LIMIT_DELAY, 5 * (2 ** (attempt - 1)))
                )
                sleep_s += random.uniform(0, 1.5)
                logger.warning(
                    f"429 rate limited. Sleeping {sleep_s:.1f}s (attempt {attempt})."
                )
                time.sleep(sleep_s)
                continue

            if r.status_code == 400:
                error_body = r.text[:500]
                logger.error(f"400 Bad Request. Response: {error_body}")
                raise requests.HTTPError(f"400 Bad Request: {error_body}", response=r)

            r.raise_for_status()
            return r

        except (
            requests.RequestException,
            requests.Timeout,
            requests.ConnectionError,
        ) as e:
            if isinstance(e, requests.HTTPError) and e.response is not None:
                if 400 <= e.response.status_code < 500:
                    raise

            last_exc = e
            sleep_s = min(30, 2**attempt + random.random())
            logger.warning(
                f"Submit failed (attempt {attempt}): {e}. Sleeping {sleep_s:.1f}s."
            )
            time.sleep(sleep_s)

    raise RuntimeError(f"Submit failed after retries: {last_exc}")


def get_with_retries(
    url: str, headers: dict, timeout_s: int, logger: logging.Logger
) -> dict:
    """
    Poll result with retries for rate limiting.
    """
    last_exc = None
    for attempt in range(1, DEFAULT_MAX_POLL_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout_s)
            if r.status_code == 429:
                sleep_s = min(DEFAULT_MAX_RATE_LIMIT_DELAY, 3 * attempt)
                logger.warning(f"429 during poll. Sleeping {sleep_s:.1f}s.")
                time.sleep(sleep_s)
                continue
            r.raise_for_status()
            return r.json()
        except (
            requests.RequestException,
            requests.Timeout,
            requests.ConnectionError,
        ) as e:
            last_exc = e
            sleep_s = min(10, 1.5**attempt + random.random())
            logger.warning(
                f"Poll failed (attempt {attempt}): {e}. Sleeping {sleep_s:.1f}s."
            )
            time.sleep(sleep_s)
    raise RuntimeError(f"Polling failed after retries: {last_exc}")


# -----------------------------
# Core API call (supports file_path or file_url)
# -----------------------------
def run_marker_once(
    *,
    api_key: str,
    file_path: Optional[Path] = None,
    file_url: Optional[str] = None,
    payload: Dict[str, Any],
    submit_timeout_s: int = DEFAULT_SUBMIT_TIMEOUT_S,
    poll_max_wait_s: int = DEFAULT_POLL_MAX_WAIT_S,
    poll_interval_s: int = DEFAULT_POLL_INTERVAL_S,
    logger: logging.Logger,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Submit a single Marker request and poll for result.
    Exactly one of file_path or file_url must be provided.
    Returns (submit_response, final_result).
    """
    api_url = "https://www.datalab.to/api/v1/marker"
    headers = {"X-API-Key": api_key, "User-Agent": "wek-nora-raggraph/1.0"}

    if file_url:
        data = dict(payload)
        data["file_url"] = file_url
        resp = post_with_retries(
            api_url,
            headers,
            data,
            files=None,
            timeout_s=submit_timeout_s,
            logger=logger,
        )
    elif file_path and file_path.exists():
        data = payload
        resp = post_file_with_retries(
            api_url, headers, data, file_path, timeout_s=submit_timeout_s, logger=logger
        )
    else:
        raise ValueError("Either file_path (existing) or file_url must be provided")
    submit = resp.json()

    check_url = submit.get("request_check_url")
    if not check_url:
        raise RuntimeError(f"No request_check_url in submit response: {submit}")

    start = time.time()
    while True:
        if (time.time() - start) > poll_max_wait_s:
            raise TimeoutError(
                f"Polling timeout after {poll_max_wait_s}s for {file_path or file_url}"
            )

        res = get_with_retries(check_url, headers, timeout_s=60, logger=logger)
        status = (res.get("status") or "unknown").lower()
        if status in ("complete", "failed", "error"):
            return submit, res

        time.sleep(poll_interval_s)


# -----------------------------
# Payload building
# -----------------------------
def build_marker_payload(
    *,
    opts: MarkerOptions,
    page_range: Optional[str],
    page_schema_json: str,
    skip_cache: bool,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "mode": opts.mode,
        "output_format": opts.output_format,
        "paginate": bool_str(opts.paginate),
        "add_block_ids": bool_str(opts.add_block_ids),
        "disable_image_extraction": bool_str(opts.disable_image_extraction),
        "disable_image_captions": bool_str(opts.disable_image_captions),
        "skip_cache": bool_str(skip_cache),
        "page_schema": page_schema_json,
    }
    if opts.force_ocr:
        payload["force_ocr"] = bool_str(True)
    if page_range:
        payload["page_range"] = page_range
    if opts.extras.strip():
        payload["extras"] = opts.extras.strip()
    if opts.segmentation_schema_json:
        payload["segmentation_schema"] = opts.segmentation_schema_json
    if opts.additional_config_json:
        payload["additional_config"] = opts.additional_config_json
    return payload


# -----------------------------
# Result unpacking (common)
# -----------------------------
def coerce_json_maybe(x: Any) -> Optional[Union[dict, list]]:
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {"_raw": x}
    return {"_raw": str(x)}


def decode_data_uri_or_b64(payload: str) -> Tuple[Optional[bytes], Optional[str]]:
    if not payload:
        return None, None
    if payload.startswith("data:") and ";base64," in payload:
        header, b64 = payload.split(";base64,", 1)
        mime = header.replace("data:", "").strip() or None
        try:
            return base64.b64decode(b64), mime
        except Exception:
            logging.warning("Failed to decode base64 image data")
            return None, None
    try:
        return base64.b64decode(payload), None
    except Exception:
        logging.warning("Failed to decode base64 image data")
        return None, None


def safe_filename(name: str) -> str:
    return Path(name).name


def write_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(p: Path, s: Optional[str]) -> None:
    if s is None:
        return
    p.write_text(s, encoding="utf-8")


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def unpack_marker_result(result: dict, out_dir: Path, logger: logging.Logger) -> None:
    """
    Unpack Datalab Marker result into stable folders.
    Compatible with both old and new pipelines.
    """
    raw_dir = out_dir / "raw"
    extracted_dir = out_dir / "extracted"
    render_dir = out_dir / "render"
    layout_dir = out_dir / "layout"
    rag_dir = out_dir / "rag"
    images_dir = out_dir / "images"

    for d in (raw_dir, extracted_dir, render_dir, layout_dir, rag_dir, images_dir):
        safe_mkdir(d)

    # Raw envelope SSOT
    write_json(raw_dir / "result.json", result)

    # Quality metrics (if present)
    quality_metrics = {
        "parse_quality_score": result.get("parse_quality_score"),
        "page_count": result.get("page_count"),
        "ocr_score": result.get("ocr_score"),
        "structure_score": result.get("structure_score"),
    }
    write_json(raw_dir / "quality_metrics.json", quality_metrics)

    # Structured extraction
    extraction_obj = coerce_json_maybe(result.get("extraction_schema_json"))
    if extraction_obj is not None:
        write_json(extracted_dir / "extraction.json", extraction_obj)

    # Render
    write_text(render_dir / "document.html", result.get("html"))
    write_text(render_dir / "document.md", result.get("markdown"))

    # Block-level json
    marker_json = coerce_json_maybe(result.get("json"))
    if marker_json is not None:
        write_json(layout_dir / "marker.json", marker_json)

    # Chunks
    chunks_obj = coerce_json_maybe(result.get("chunks"))
    if chunks_obj is not None:
        write_json(rag_dir / "chunks.json", chunks_obj)

        blocks = None
        if isinstance(chunks_obj, list):
            blocks = chunks_obj
        elif isinstance(chunks_obj, dict) and isinstance(
            chunks_obj.get("blocks"), list
        ):
            blocks = chunks_obj["blocks"]

        if blocks:
            with (rag_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
                for i, ch in enumerate(blocks):
                    if isinstance(ch, dict):
                        ch.setdefault("chunk_id", i)
                        f.write(json.dumps(ch, ensure_ascii=False) + "\n")
                    else:
                        f.write(
                            json.dumps(
                                {"chunk_id": i, "text": str(ch)}, ensure_ascii=False
                            )
                            + "\n"
                        )

    # Images
    images_obj = coerce_json_maybe(result.get("images"))
    if images_obj is None:
        return

    manifest = {"generated_at": utc_now_iso(), "count": 0, "items": []}

    if isinstance(images_obj, dict):
        for filename, b64 in images_obj.items():
            blob, mime = decode_data_uri_or_b64(b64)
            if not blob:
                continue
            safe_name = sanitize_path_component(filename)
            try:
                (images_dir / safe_name).write_bytes(blob)
                manifest["items"].append(
                    {"filename": safe_name, "mime_type": mime, "size_bytes": len(blob)}
                )
            except Exception as e:
                logger.warning(f"Failed to write image {safe_name}: {e}")

    elif isinstance(images_obj, list):
        for i, img in enumerate(images_obj):
            if not isinstance(img, dict):
                continue
            b64 = img.get("image") or img.get("data") or img.get("base64")
            if not b64:
                continue
            blob, mime = decode_data_uri_or_b64(b64)
            mime = img.get("mime_type") or img.get("mimetype") or mime
            if not blob:
                continue

            ext = mimetypes.guess_extension(mime) if mime else None
            if mime in ("image/jpeg", "image/jpg"):
                ext = ".jpg"
            if not ext:
                ext = ".png"
            filename = sanitize_path_component(f"figure_{i:04d}{ext}")

            try:
                (images_dir / filename).write_bytes(blob)
                meta = {
                    k: v for k, v in img.items() if k not in ("image", "data", "base64")
                }
                meta.update(
                    {
                        "filename": filename,
                        "index": i,
                        "mime_type": mime,
                        "size_bytes": len(blob),
                    }
                )
                manifest["items"].append(meta)
            except Exception as e:
                logger.warning(f"Failed to write image {filename}: {e}")

    manifest["count"] = len(manifest["items"])
    if manifest["count"] > 0:
        write_json(images_dir / "manifest.json", manifest)


# -----------------------------
# Schema loading
# -----------------------------
def load_schema(schema_path: Optional[Path], logger: logging.Logger) -> dict:
    """
    Load page_schema JSON from file, or return embedded minimal stable schema.
    """
    EMBEDDED_MINIMAL_STABLE_SCHEMA: Dict[str, Any] = {
        "type": "object",
        "title": "Minimal Stable Scientific Summary",
        "description": "Minimal, stable extraction across heterogeneous scientific PDFs.",
        "properties": {
            "article_title": {
                "type": "string",
                "description": "Exact paper title (first page).",
            },
            "authors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Authors list if present.",
            },
            "publication_year": {
                "type": "integer",
                "description": "4-digit year if explicitly stated.",
            },
            "doi": {"type": "string", "description": "DOI if present."},
            "journal_or_source": {
                "type": "string",
                "description": "Journal or source if present.",
            },
            "abstract": {
                "type": "string",
                "description": "Short abstract summary (max 2 sentences) if present.",
            },
            "research_question": {
                "type": "string",
                "description": "Main research objective.",
            },
            "methods": {"type": "string", "description": "Methods summary."},
            "results": {"type": "string", "description": "Key results."},
            "conclusions": {"type": "string", "description": "Main conclusions."},
            "limitations": {"type": "string", "description": "Stated limitations."},
            "key_entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Important entities.",
            },
            "key_claims": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Central claims.",
            },
        },
        "required": ["article_title"],
    }

    if schema_path is None:
        return EMBEDDED_MINIMAL_STABLE_SCHEMA

    if not schema_path.exists():
        logger.warning(
            f"Schema file not found: {schema_path}. Using embedded minimal stable schema."
        )
        return EMBEDDED_MINIMAL_STABLE_SCHEMA

    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, IOError) as e:
        logger.warning(
            f"Failed to parse schema file {schema_path}: {e}. Using embedded minimal stable schema."
        )
        return EMBEDDED_MINIMAL_STABLE_SCHEMA
