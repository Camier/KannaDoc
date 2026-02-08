#!/usr/bin/env python3
"""
Datalab Marker extraction runner (single-pass, minimal, stable)
- Uses shared datalab_marker_api module with file_url support and retry logic.
- Maintains backward compatibility with existing scripts.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import requests

# Import shared API module
from .datalab_api import (
    MarkerOptions,
    build_marker_payload,
    load_api_key as shared_load_api_key,
    load_schema as shared_load_schema,
    run_marker_once,
    unpack_marker_result,
    utc_now_iso,
    safe_mkdir,
    write_json,
    write_text,
    safe_filename,
    coerce_json_maybe,
    DEFAULT_MODE,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PAGINATE,
    DEFAULT_ADD_BLOCK_IDS,
    DEFAULT_DISABLE_IMAGE_EXTRACTION,
    DEFAULT_DISABLE_IMAGE_CAPTIONS,
    DEFAULT_EXTRAS,
    DEFAULT_SUBMIT_TIMEOUT_S,
    DEFAULT_POLL_MAX_WAIT_S,
    DEFAULT_POLL_INTERVAL_S,
)

# Import shared utilities
from .datalab_utils import (
    calculate_sha256_string,
    is_valid_pdf,
    sanitize_path_component,
    generate_unique_id,
    validate_file_size,
    DATALAB_ROOT,
)


# -----------------------------
# Logging
# -----------------------------
def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("datalab_process")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_dir / "datalab_process.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger


# -----------------------------
# Main processing
# -----------------------------
def process_document(
    *,
    input_ref: str,
    is_file_url: bool,
    root: Path,
    output_root: Path,
    schema_path: Optional[Path],
    no_schema: bool,
    mode: str,
    output_format: str,
    add_block_ids: bool,
    paginate: bool,
    disable_image_extraction: bool,
    disable_image_captions: bool,
    extras: str,
    force_ocr: bool,
    skip_cache: bool,
    page_range: Optional[str],
    submit_timeout_s: int,
    poll_max_wait_s: int,
    poll_interval_s: int,
    fallback_conversion_only: bool,
    logger: logging.Logger,
) -> Optional[Path]:
    """
    Process a single document (local PDF or file_url) using Datalab Marker.
    Returns path to output directory if successful, None otherwise.
    """
    # Determine input source
    file_path = None
    file_url = None
    if is_file_url:
        file_url = input_ref
        doc_id = calculate_sha256_string(input_ref)
        display_name = input_ref
        safe_stem = safe_filename(input_ref).replace("://", "_").replace("/", "_")[:60]
    else:
        file_path = Path(input_ref)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")
        # Validate PDF format
        if not is_valid_pdf(file_path):
            raise ValueError(f"Invalid PDF file: {file_path}")
        # Validate file size
        validate_file_size(file_path)
        doc_id = calculate_sha256_string(file_path.name)
        display_name = file_path.name
        safe_stem = file_path.stem[:60].replace(" ", "_")

    # Create output directory (timestamped with unique ID to prevent collisions)
    out_dir = (
        output_root
        / f"{time.strftime('%Y%m%d_%H%M%S')}_{generate_unique_id()}_{safe_stem}"
    )
    safe_mkdir(out_dir)
    raw_dir = out_dir / "raw"
    safe_mkdir(raw_dir)

    write_text(raw_dir / "doc_id.txt", doc_id)

    # Load schema (unless disabled)
    schema = None if no_schema else shared_load_schema(schema_path, logger)

    # Build Marker options
    opts = MarkerOptions(
        mode=mode,
        output_format=output_format,
        paginate=paginate,
        add_block_ids=add_block_ids,
        disable_image_extraction=disable_image_extraction,
        disable_image_captions=disable_image_captions,
        extras=extras,
        force_ocr=force_ocr,
        segmentation_schema_json=None,
        additional_config_json=None,
    )

    # Build payload
    page_schema_json = json.dumps(schema) if schema else ""
    payload = build_marker_payload(
        opts=opts,
        page_range=page_range if not page_range or page_range.lower() != "all" else "",
        page_schema_json=page_schema_json,
        skip_cache=skip_cache,
    )

    # Record request metadata
    write_json(
        raw_dir / "request.json",
        {
            "created_at": utc_now_iso(),
            "doc_id": doc_id,
            "input": input_ref,
            "is_file_url": is_file_url,
            "page_range": page_range,
            "payload": payload,
            "schema_path": str(schema_path) if schema_path else None,
            "no_schema": no_schema,
        },
    )

    print(
        f"[INFO] Processing: {display_name} (mode={mode}, page_range={page_range}, schema={'off' if no_schema else 'on'})"
    )

    # Load API key (shared function respects root/data/.datalab_api_key)
    api_key = shared_load_api_key(root)

    def _run_attempt(
        attempt: int, attempt_payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Run a single Marker attempt and save intermediate results."""
        submit, result = run_marker_once(
            api_key=api_key,
            file_path=file_path,
            file_url=file_url,
            payload=attempt_payload,
            submit_timeout_s=submit_timeout_s,
            poll_max_wait_s=poll_max_wait_s,
            poll_interval_s=poll_interval_s,
            logger=logger,
        )
        write_json(raw_dir / f"attempt{attempt}_submit_response.json", submit)
        write_text(
            raw_dir / f"attempt{attempt}_check_url.txt",
            submit.get("request_check_url", ""),
        )
        # Avoid duplicating the canonical raw output.
        #
        # `app.lib.datalab.datalab_api` writes `raw/result.json`, which is the canonical
        # filename used across the codebase. Historically this module also wrote
        # `attempt1_final_result.json`, which was a 1:1 duplicate and a drift risk.
        #
        # We still keep attemptN_final_result.json for retry attempts (N>1) to aid debugging.
        if attempt > 1:
            write_json(raw_dir / f"attempt{attempt}_final_result.json", result)
        return submit, result

    try:
        _, res1 = _run_attempt(1, payload)
    except (
        requests.RequestException,
        ValueError,
        FileNotFoundError,
        TimeoutError,
    ) as e:
        logger.error(f"Unexpected error: {e}")
        write_text(raw_dir / "error_submit.txt", str(e))
        print(f"[ERROR] Error: {e}")
        return None

    status = (res1.get("status") or "").lower()
    success = res1.get("success", None)
    error_msg = str(res1.get("error") or "")

    if status == "complete" and success is True:
        print("[OK] Success. Unpacking...")
        unpack_marker_result(res1, out_dir, logger)
        print(f"[OK] Output saved to: {out_dir}")
        return out_dir

    # Failure attempt 1
    print(f"[ERROR] Processing failed: {error_msg or 'Unknown error'}")
    logger.error(f"Processing failed (attempt 1): {error_msg}")

    # Fallback conversion-only (if JSON repair failed and fallback enabled)
    if (
        "json repair failed" in error_msg.lower()
        and fallback_conversion_only
        and not no_schema
    ):
        print(
            "   [INFO] Tip: Structured extraction failed. Retrying conversion-only (no page_schema)..."
        )
        # Build payload without schema
        payload2 = build_marker_payload(
            opts=opts,
            page_range=page_range
            if not page_range or page_range.lower() != "all"
            else "",
            page_schema_json="",
            skip_cache=True,  # avoid cached broken extraction
        )
        try:
            _, res2 = _run_attempt(2, payload2)
            status2 = (res2.get("status") or "").lower()
            success2 = res2.get("success", None)
            error2 = str(res2.get("error") or "")
            if status2 == "complete" and success2 is True:
                print("[OK] Fallback conversion-only succeeded. Unpacking...")
                unpack_marker_result(res2, out_dir, logger)
                print(f"[OK] Output saved to: {out_dir}")
                return out_dir
            print(
                f"[ERROR] Fallback conversion-only failed: {error2 or 'Unknown error'}"
            )
            logger.error(f"Fallback failed (attempt 2): {error2}")
        except (
            requests.RequestException,
            ValueError,
            FileNotFoundError,
            TimeoutError,
        ) as e:
            print(f"[ERROR] Fallback attempt error: {e}")
            logger.error(f"Fallback attempt error: {e}")

    return None


# -----------------------------
# CLI entry point
# -----------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Datalab Marker extraction on a single document."
    )
    parser.add_argument("input", help="Local PDF path or URL (use --file-url for URLs)")
    parser.add_argument(
        "--file-url", action="store_true", help="Treat input as file_url (http/https)."
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("DATALAB_ROOT", str(DATALAB_ROOT)),
        help="Project root (default: DATALAB_ROOT env var or /LAB/@thesis/datalab)",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Output directory root (default: <root>/data/datextract)",
    )
    parser.add_argument(
        "--schema", default=None, help="Path to JSON schema file for page_schema."
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Disable structured extraction (conversion-only).",
    )
    parser.add_argument(
        "--mode", default=DEFAULT_MODE, choices=["fast", "balanced", "accurate"]
    )
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument(
        "--page-range", default="all", help='Use "all" or ranges like "0-6". 0-indexed.'
    )
    parser.add_argument("--paginate", action="store_true", default=DEFAULT_PAGINATE)
    parser.add_argument(
        "--no-add-block-ids",
        action="store_true",
        help="Disable add_block_ids (HTML will not include data-block-id).",
    )
    parser.add_argument(
        "--disable-image-extraction",
        action="store_true",
        default=DEFAULT_DISABLE_IMAGE_EXTRACTION,
    )
    parser.add_argument(
        "--disable-image-captions",
        action="store_true",
        default=DEFAULT_DISABLE_IMAGE_CAPTIONS,
    )
    parser.add_argument(
        "--extras",
        default=DEFAULT_EXTRAS,
        help='Comma-separated extras, e.g. "extract_links".',
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        default=False,
        help="Force OCR on all pages (useful for scanned/historical documents).",
    )
    parser.add_argument("--skip-cache", action="store_true", default=False)
    parser.add_argument(
        "--submit-timeout",
        type=int,
        default=DEFAULT_SUBMIT_TIMEOUT_S,
        help="Submit request timeout (seconds).",
    )
    parser.add_argument(
        "--poll-max-wait",
        type=int,
        default=DEFAULT_POLL_MAX_WAIT_S,
        help="Max polling wait (seconds).",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL_S,
        help="Polling interval (seconds).",
    )
    parser.add_argument(
        "--fallback-conversion-only",
        action="store_true",
        default=True,
        help="On JSON repair failed, retry conversion-only (no schema) to salvage json/html/chunks.",
    )
    parser.add_argument(
        "--no-fallback-conversion-only",
        dest="fallback_conversion_only",
        action="store_false",
        help="Disable conversion-only fallback.",
    )

    args = parser.parse_args()

    root = Path(args.root)
    output_root = (
        Path(args.output_root) if args.output_root else (root / "data" / "datextract")
    )
    schema_path = Path(args.schema) if args.schema else None

    logger = setup_logger(root / "data" / "logs")

    try:
        out = process_document(
            input_ref=args.input,
            is_file_url=args.file_url,
            root=root,
            output_root=output_root,
            schema_path=schema_path,
            no_schema=args.no_schema,
            mode=args.mode,
            output_format=args.output_format,
            add_block_ids=not args.no_add_block_ids,
            paginate=args.paginate,
            disable_image_extraction=args.disable_image_extraction,
            disable_image_captions=args.disable_image_captions,
            extras=args.extras,
            force_ocr=args.force_ocr,
            skip_cache=args.skip_cache,
            page_range=args.page_range,
            submit_timeout_s=args.submit_timeout,
            poll_max_wait_s=args.poll_max_wait,
            poll_interval_s=args.poll_interval,
            fallback_conversion_only=args.fallback_conversion_only,
            logger=logger,
        )
        if out is None:
            sys.exit(2)
        sys.exit(0)
    except (
        requests.RequestException,
        ValueError,
        FileNotFoundError,
        TimeoutError,
        OSError,
    ) as e:
        logger.error(f"Fatal: {e}")
        print(f"[ERROR] Fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
