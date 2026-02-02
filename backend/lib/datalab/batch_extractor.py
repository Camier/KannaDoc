#!/usr/bin/env python3
"""
Unified DataLab Extraction Runner
Consolidates all batch processing functionality with CLI interface.
"""

import sys
import time
import logging
import argparse
import json
import os
import random
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Import from main processor
try:
    from .datalab_process import process_document, setup_logger
    from .normalization import normalize_document
    from .schemas.raw_envelope import (
        RawMarkerEnvelope,
        DatalabMetadata,
        DatalabOptions,
        Provenance,
    )
except ImportError as e:
    print(f"[FAIL] Could not import required modules: {e}")
    sys.exit(1)

# Configuration
ROOT_DIR = Path(os.environ.get("DATALAB_ROOT", "/LAB/@thesis/datalab"))
PDF_DIR = ROOT_DIR / "ALL_FLAT"
DATA_DIR = ROOT_DIR / "data"
CATALOG_FILE = DATA_DIR / "catalog.json"
OUTPUT_ROOT = DATA_DIR / "datextract"
LOG_DIR = DATA_DIR / "logs"

# Test files for --mode test
TEST_FILES = [
    "2021 - Ateba - A Chewable Cure Kanna Biological and Pharmaceutical Properties of Sceletium tortuosum.pdf",
    "2011 - Spina - PDE4-inhibitors A novel targeted therapy for obstructive airways disease.pdf",
    "2020 - al. - Ergogenic Effects of 8 Days of Sceletium tortuosum Supplementation on Mood Visual Tracking and React.pdf",
    "2025 - Lepule - Neuroprotective and neurorestorative properties of Mesembryanthemum tortuosum in a Parkinsons diseas.pdf",
    "2024 - Kang - The Glucose-Lowering Effect of Mesembryanthemum crystallinum and D-Pinitol Studies on Insulin Secret.pdf",
    "2004 - O'Donnell - Antidepressant effects of inhibitors of cAMP phosphodiesterase PDE4.pdf",
]

# Setup logging
LOG_DIR.mkdir(exist_ok=True, parents=True)
logger = setup_logger(LOG_DIR)


def run_normalization(result_dir: Path) -> bool:
    """Run normalization on extracted result directory.

    Creates normalized.json with images persisted to _assets/.
    Returns True on success, False on failure.
    """
    try:
        raw_result_path = result_dir / "raw" / "result.json"
        if not raw_result_path.exists():
            logger.warning(f"[NORM] No result.json found in {result_dir}")
            return False

        raw_result = json.loads(raw_result_path.read_text(encoding="utf-8"))

        # Read doc_id
        doc_id_path = result_dir / "raw" / "doc_id.txt"
        doc_id = (
            doc_id_path.read_text().strip() if doc_id_path.exists() else result_dir.name
        )

        # Read request.json for metadata
        request_path = result_dir / "raw" / "request.json"
        request_data = (
            json.loads(request_path.read_text()) if request_path.exists() else {}
        )

        # Build envelope
        envelope = RawMarkerEnvelope(
            doc_id=doc_id,
            datalab=DatalabMetadata(
                request_id=request_data.get("request_id", "unknown"),
                request_check_url=request_data.get("check_url"),
                options=DatalabOptions(
                    output_format=request_data.get("output_format", "json,chunks,html"),
                    mode=request_data.get("mode", "balanced"),
                    page_range=request_data.get("page_range"),
                    add_block_ids=request_data.get("add_block_ids", True),
                    page_schema=request_data.get("page_schema"),
                ),
            ),
            raw_result=raw_result,
            provenance=Provenance(
                source_file=request_data.get("source_file", "unknown"),
                sha256=request_data.get("sha256", "unknown"),
                retrieved_at=datetime.now(),
                collector_id="datalab_pipeline_v2",
                ingest_batch=datetime.now().strftime("%Y%m%d"),
            ),
        )

        # Assets go inside result_dir
        assets_root = result_dir / "_assets" / doc_id

        # Normalize
        normalized = normalize_document(envelope, assets_root=assets_root)

        # Write normalized.json
        output_path = result_dir / "normalized.json"
        output_path.write_text(normalized.model_dump_json(indent=2), encoding="utf-8")

        n_chunks = len(normalized.chunks)
        n_images = len(normalized.images)
        n_figures = len(normalized.figures)
        logger.info(
            f"[NORM] {doc_id[:40]}... -> {n_chunks} chunks, {n_images} images, {n_figures} figures"
        )
        return True

    except Exception as e:
        logger.error(
            f"[NORM] Normalization failed for {result_dir}: {e}", exc_info=True
        )
        return False


def load_catalog():
    """Load catalog and return map of {filename: datalab_reference}."""
    if not CATALOG_FILE.exists():
        logger.warning("Catalog not found. Will use local file uploads.")
        return {}

    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        ref_map = {}
        for entry in data.values():
            if entry.get("status") == "uploaded" and entry.get("file_reference"):
                ref_map[entry["filename"]] = entry["file_reference"]

        logger.info(f"Loaded {len(ref_map)} catalog references.")
        return ref_map
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        return {}


def process_wrapper(
    pdf_path: Path,
    page_range: str,
    ref_map: dict,
    catalog_only: bool,
    api_mode: str,
    output_dir: Optional[str] = None,
    no_schema: bool = True,
    chunks_only: bool = False,
    force_ocr: bool = False,
    schema_path_override: Optional[str] = None,
):
    """Wrapper to handle processing of a single file."""
    filename = pdf_path.name

    # Determine input source (catalog reference or local file)
    input_source = None
    is_file_url = False
    source_type = "LOCAL"

    # Always prefer local file upload over catalog references
    # datalab:// URIs only work in Workflow context, not direct Marker API
    if pdf_path.exists():
        input_source = str(pdf_path)
        is_file_url = False
        source_type = "LOCAL"
        logger.info(f"[PROC] Processing ({source_type}): {filename}")
    elif filename in ref_map and not catalog_only:
        # Fallback to catalog if local file doesn't exist (edge case)
        logger.warning(
            f"[WARN] Local file not found, catalog refs not supported for Marker API: {filename}"
        )
        return filename, "skipped_no_local", None
    elif catalog_only:
        logger.warning(
            f"[SKIP] Skipping (catalog-only mode not supported for Marker API): {filename}"
        )
        return filename, "skipped_no_catalog", None
    else:
        logger.error(f"[FAIL] File not found: {pdf_path}")
        return filename, "file_not_found", None

    output_root_path = Path(output_dir) if output_dir else OUTPUT_ROOT

    if schema_path_override:
        schema_path = Path(schema_path_override)
    else:
        schema_path = ROOT_DIR / "data" / "notes" / "page_schema_simple.json"

    # Determine output format based on flags
    # RAG minimal SHOULD still include 'json' for bbox/anchors (block lookup)
    if chunks_only:
        output_format = "json,chunks"
    else:
        output_format = "json,html,markdown,chunks"

    # add_block_ids only applies when output_format includes 'html'
    add_block_ids = "html" in {x.strip() for x in output_format.split(",")}

    # Validate schema file exists (only needed if using schema)
    use_no_schema = no_schema
    if not no_schema and not schema_path.exists():
        logger.warning(
            f"[WARN] Schema file not found: {schema_path}. Proceeding without schema."
        )
        use_no_schema = True

    try:
        result_dir = process_document(
            input_ref=input_source,
            is_file_url=is_file_url,
            root=ROOT_DIR,
            output_root=output_root_path,
            schema_path=schema_path if not use_no_schema else None,
            no_schema=use_no_schema,
            mode=api_mode,
            output_format=output_format,
            add_block_ids=add_block_ids,
            paginate=True,
            disable_image_extraction=False,
            disable_image_captions=False,
            extras="extract_links",
            force_ocr=force_ocr,
            skip_cache=False,
            # 'all' is not a documented page_range value; omit when wanting full doc
            page_range=None if (page_range or "").lower() == "all" else page_range,
            submit_timeout_s=300,
            poll_max_wait_s=2700,
            poll_interval_s=5,
            fallback_conversion_only=True,
            logger=logger,
        )

        if result_dir:
            logger.info(f"[OK] Completed: {filename}")
            run_normalization(Path(result_dir))
            return filename, "success", result_dir
        else:
            logger.error(f"[FAIL] Failed: {filename}")
            return filename, "failed", None

    except Exception as e:
        logger.error(f"[FAIL] Exception processing {filename}: {e}", exc_info=True)
        return filename, "error", None


def select_files(mode: str, count: Optional[int] = None) -> list:
    """Select files based on mode."""
    if not PDF_DIR.exists():
        logger.error(f"PDF directory not found: {PDF_DIR}")
        return []

    all_pdfs = sorted(list(PDF_DIR.glob("*.pdf")))

    if mode == "test":
        # Use predefined test files
        selected = []
        for test_file in TEST_FILES:
            pdf_path = PDF_DIR / test_file
            if pdf_path.exists():
                selected.append(pdf_path)
            else:
                logger.warning(f"Test file not found: {test_file}")
        return selected

    elif mode == "sample":
        # Random sample
        sample_count = count if count else 10
        if sample_count >= len(all_pdfs):
            return all_pdfs
        return random.sample(all_pdfs, sample_count)

    elif mode == "full":
        # All PDFs
        return all_pdfs

    else:
        logger.error(f"Unknown mode: {mode}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Unified DataLab extraction runner with multiple modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test on 6 predefined files (all pages, no schema - reliable)
  python3 -m lib.batch_extractor --mode test --no-schema
  
  # RAG-optimized extraction (chunks only, no schema)
  python3 -m lib.batch_extractor --mode test --no-schema --chunks-only
  
  # Full corpus extraction with schema (may hit 400 errors)
  python3 -m lib.batch_extractor --mode full --workers 3
  
  # Use only catalog references (no local upload)
  python3 -m lib.batch_extractor --mode full --catalog-only --no-schema
  
  # Custom output directory
  python3 -m lib.batch_extractor --mode full --output-dir data/FULL_EXTRACTION --no-schema
        """,
    )

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["test", "sample", "full"],
        help="Processing mode: test (6 files), sample (random subset), full (all)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of files for sample mode (default: 10)",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default="all",
        help="Page range to extract (default: all for complete document)",
    )
    parser.add_argument(
        "--workers", type=int, default=2, help="Number of parallel workers (default: 2)"
    )

    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only process files that exist in catalog (skip local uploads)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for extraction results",
    )

    # Fix: Exposed API Mode with correct default
    parser.add_argument(
        "--api-mode",
        type=str,
        default="accurate",
        help="DataLab API Mode (accurate, balanced, fast). Default: accurate",
    )

    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Disable page_schema extraction (avoids 400 errors, more reliable)",
    )

    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Path to custom page_schema JSON file (overrides default)",
    )

    parser.add_argument(
        "--chunks-only",
        action="store_true",
        help="Request only chunks output format (optimal for RAG)",
    )

    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force OCR on all pages (for scanned/historical documents)",
    )

    args = parser.parse_args()

    # Resolve schema path
    if args.schema:
        resolved_schema = str(Path(args.schema).resolve())
        if not Path(resolved_schema).exists():
            logger.error(f"Schema file not found: {resolved_schema}")
            return 1
    else:
        resolved_schema = None

    # Worker limit validation
    max_workers = min(args.workers, os.cpu_count() or 4)

    # Handle "all" pages
    page_range = args.pages
    if page_range.lower() == "all":
        page_range = "all"

    # Banner
    logger.info("=" * 70)
    logger.info("[INFO] DATALAB FULL EXTRACTION RUNNER")
    logger.info(f"Mode:     {args.mode}")
    logger.info(f"API Mode: {args.api_mode}")
    logger.info(f"Pages:    {page_range if page_range else 'ALL PAGES'}")
    logger.info(f"Workers:  {max_workers}")
    logger.info(
        f"Schema:   {'Disabled' if args.no_schema else 'Enabled with fallback'}"
    )
    logger.info(
        f"Output:   {'chunks only' if args.chunks_only else 'json,html,markdown,chunks'}"
    )
    logger.info(f"Catalog:  {'Only' if args.catalog_only else 'Prefer with fallback'}")
    if args.output_dir:
        logger.info(f"Dir:      {args.output_dir}")
    logger.info("=" * 70)

    # Select files
    pdfs = select_files(args.mode, args.count)
    logger.info(f"Selected {len(pdfs)} PDF files for processing.")

    if not pdfs:
        logger.error("No files to process. Exiting.")
        return 1

    # Load catalog
    ref_map = load_catalog()

    # Statistics
    stats = {"success": 0, "failed": 0, "error": 0, "skipped_no_catalog": 0}
    start_time = time.time()

    # Process with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_wrapper,
                pdf,
                page_range,
                ref_map,
                args.catalog_only,
                args.api_mode,
                args.output_dir,
                args.no_schema,
                args.chunks_only,
                args.force_ocr,
                resolved_schema,
            ): pdf
            for pdf in pdfs
        }

        for i, future in enumerate(as_completed(futures), 1):
            pdf = futures[future]
            try:
                filename, status, result_dir = future.result()
                stats[status] = stats.get(status, 0) + 1

                # Progress indicator
                progress = f"[{i}/{len(pdfs)}]"
                if status == "success":
                    print(f"{progress} [OK] {filename}")
                elif status == "skipped_no_catalog":
                    print(f"{progress} [SKIP] {filename} (not in catalog)")
                else:
                    print(f"{progress} [FAIL] {filename} ({status})")

            except Exception as exc:
                logger.error(
                    f"Future generated exception for {pdf.name}: {exc}", exc_info=True
                )
                stats["error"] += 1

    # Summary
    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("FULL EXTRACTION COMPLETE")
    logger.info(f"Total files:  {len(pdfs)}")
    logger.info(f"Success:      {stats['success']}")
    if stats["skipped_no_catalog"] > 0:
        logger.info(f"No catalog:   {stats['skipped_no_catalog']}")
    logger.info(f"Failed:       {stats['failed']}")
    logger.info(f"Errors:       {stats['error']}")
    logger.info(f"Elapsed:      {elapsed:.1f}s ({elapsed / 60:.1f}min)")
    logger.info("=" * 70)

    return 0 if stats["failed"] + stats["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
