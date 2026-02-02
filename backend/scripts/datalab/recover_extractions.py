#!/usr/bin/env python3
"""
DataLab Recovery CLI

Recover lost extraction outputs by:
1. Building request_id -> folder mapping from existing extractions
2. Parsing logs to find processed PDFs and their request_ids
3. Re-downloading results from Marker API using stored check_urls
4. Or re-extracting from scratch if needed
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Setup paths
ROOT = Path("/LAB/@thesis/datalab")
DEFAULT_OUTPUT_DIR = ROOT / "data" / "extractions" / "recovered"
LOG_DIR = ROOT / "data" / "logs"
PRODUCTION_DIR = ROOT / "data" / "extractions" / "production"
STAGING_DIR = ROOT / "data" / "extractions" / "staging"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "recovery.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_api_key():
    """Load API key from file."""
    key_file = ROOT / "data" / ".datalab_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    raise ValueError("API key not found")


def get_with_retries(url, headers, timeout_s, logger):
    """Simple GET with retries."""
    import requests

    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=headers, timeout=timeout_s)
            if r.status_code == 429:
                time.sleep(min(60, 3 * attempt))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(min(10, 1.5**attempt + random.random()))
    raise RuntimeError("Max retries exceeded")


def sanitize_path_component(component: str) -> str:
    """Sanitize string for safe filename use."""
    if not isinstance(component, str):
        component = str(component)
    sanitized = component.replace("..", "").replace("...", "")
    sanitized = sanitized.replace("/", "_").replace("\\", "_")
    sanitized = "".join(char for char in sanitized if ord(char) >= 32)
    sanitized = re.sub(r"[^\w\s\-\.\(\)]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip(". ")
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized or "unnamed"


def unpack_result(result: dict, out_dir: Path, logger):
    """Unpack Marker API result to directory."""
    import requests

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    # Save raw result
    (raw_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Save chunks
    chunks = result.get("chunks", [])
    if chunks:
        chunks_file = out_dir / "chunks.jsonl"
        with open(chunks_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Save HTML/Markdown
    html = result.get("html", "")
    if html:
        (out_dir / "document.html").write_text(html, encoding="utf-8")

    markdown = result.get("markdown", "")
    if markdown:
        (out_dir / "document.md").write_text(markdown, encoding="utf-8")

    logger.info(f"Unpacked to: {out_dir}")


def find_request_json_files(search_dir: Path) -> List[Path]:
    """Find all submit_response.json files."""
    json_files = []
    if not search_dir.exists():
        return json_files

    for extraction_dir in search_dir.iterdir():
        if not extraction_dir.is_dir():
            continue
        raw_dir = extraction_dir / "raw"
        if raw_dir.exists():
            for json_file in raw_dir.glob("*submit_response.json"):
                json_files.append(json_file)

    return json_files


def extract_request_mapping(search_dirs: List[Path]) -> Dict[str, Dict[str, Any]]:
    """Build mapping: request_id -> {folder, check_url, pdf_name}."""
    mapping = {}

    for search_dir in search_dirs:
        logger.info(f"Scanning {search_dir}...")
        json_files = find_request_json_files(search_dir)

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                request_id = data.get("request_id")
                check_url = data.get("request_check_url")

                if not request_id:
                    continue

                folder = json_file.parent.parent
                folder_name = folder.name

                pdf_match = re.search(r"\d{8}_\d{6}_[a-f0-9]+_(.+)", folder_name)
                pdf_name = pdf_match.group(1) if pdf_match else folder_name

                mapping[request_id] = {
                    "folder": str(folder),
                    "folder_name": folder_name,
                    "check_url": check_url,
                    "pdf_name": pdf_name,
                    "json_file": str(json_file),
                }
            except Exception as e:
                logger.warning(f"Failed to parse {json_file}: {e}")

    return mapping


def parse_extraction_log(log_path: Path) -> List[Dict[str, Any]]:
    """Parse extraction log to find processed PDFs and their outputs."""
    entries = []

    if not log_path.exists():
        logger.error(f"Log file not found: {log_path}")
        return entries

    # Try to find Request IDs (older logs)
    request_pattern = re.compile(
        r"Request ID:\s*([^,]+),\s*Check URL:\s*(https://[^\s]+)"
    )
    # Find output directories
    output_pattern = re.compile(r"\[OK\]\s*Output saved to:\s*(.+?)(?:\s*$|\s+\[)")
    # Find processed PDFs (batch_extractor format)
    pdf_pattern = re.compile(r"\[(\d+/\d+)\]\s+\[OK\]\s+(.+\.pdf)")
    # Find processing lines
    proc_pattern = re.compile(r"\[INFO\]\s+Processing:\s+(.+?)\.pdf")

    current_entry = {}
    pdf_to_entry = {}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Match Request ID line
            req_match = request_pattern.search(line)
            if req_match:
                current_entry["request_id"] = req_match.group(1).strip()
                current_entry["check_url"] = req_match.group(2).strip()
                continue

            # Match Output saved line
            out_match = output_pattern.search(line)
            if out_match:
                output_dir = out_match.group(1).strip()
                current_entry["output_dir"] = output_dir
                current_entry["status"] = "ok"

                # Try to extract PDF name from output dir
                dir_name = Path(output_dir).name
                pdf_match = re.search(r"\d{8}_\d{6}_[a-f0-9]+_(.+)", dir_name)
                if pdf_match:
                    pdf_name = pdf_match.group(1).replace("_", " ") + ".pdf"
                    current_entry["pdf_name"] = pdf_name
                    pdf_to_entry[pdf_name] = current_entry.copy()

                entries.append(current_entry)
                current_entry = {}
                continue

            # Match [N/M] [OK] filename.pdf pattern
            pdf_match = pdf_pattern.search(line)
            if pdf_match:
                pdf_name = pdf_match.group(2).strip()
                if pdf_name not in pdf_to_entry:
                    pdf_to_entry[pdf_name] = {"pdf_name": pdf_name, "status": "ok"}
                continue

            # Match Processing line
            proc_match = proc_pattern.search(line)
            if proc_match:
                pdf_base = proc_match.group(1).strip()
                pdf_name = pdf_base + ".pdf"
                if pdf_name not in pdf_to_entry:
                    pdf_to_entry[pdf_name] = {
                        "pdf_name": pdf_name,
                        "status": "processing",
                    }

    # Convert dict to list
    entries = list(pdf_to_entry.values())
    return entries

    request_pattern = re.compile(
        r"Request ID:\s*([^,]+),\s*Check URL:\s*(https://[^\s]+)"
    )
    output_pattern = re.compile(r"\[OK\]\s*Output saved to:\s*(.+?)(?:\s*$|\s+\[)")

    current_entry = {}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            req_match = request_pattern.search(line)
            if req_match:
                current_entry["request_id"] = req_match.group(1).strip()
                current_entry["check_url"] = req_match.group(2).strip()
                continue

            out_match = output_pattern.search(line)
            if out_match and current_entry.get("request_id"):
                current_entry["output_dir"] = out_match.group(1).strip()
                current_entry["status"] = "ok"
                entries.append(current_entry)
                current_entry = {}

    return entries


def recover_by_request_id(
    request_id: str,
    check_url: str,
    output_dir: Path,
    api_key: str,
    dry_run: bool = False,
) -> bool:
    """Recover a single extraction by request_id."""
    logger.info(f"Recovering: {request_id}")

    if dry_run:
        logger.info("  [DRY RUN]")
        return True

    headers = {"X-API-Key": api_key}

    try:
        import requests

        result = get_with_retries(check_url, headers, 30, logger)
        status = result.get("status", "").lower()

        if status != "complete":
            logger.error(f"  Status: {status}")
            return False

        safe_name = sanitize_path_component(request_id)
        recovery_dir = output_dir / f"recovered_{safe_name}"
        recovery_dir.mkdir(parents=True, exist_ok=True)

        unpack_result(result, recovery_dir, logger)
        logger.info(f"  [OK] Recovered to: {recovery_dir}")
        return True

    except Exception as e:
        logger.error(f"  [ERROR] {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover DataLab extractions")
    parser.add_argument(
        "--scan-existing", action="store_true", help="Scan existing extractions"
    )
    parser.add_argument("--parse-log", type=Path, help="Parse extraction log")
    parser.add_argument(
        "--report", action="store_true", help="Generate recovery report"
    )
    parser.add_argument("--from-log", type=Path, help="Log file for report/recovery")
    parser.add_argument("--recover-by-id", type=str, help="Recover specific request_id")
    parser.add_argument("--check-url", type=str, help="Check URL for recovery")
    parser.add_argument(
        "--recover-all", action="store_true", help="Recover all from log"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if not any(
        [
            args.scan_existing,
            args.parse_log,
            args.report,
            args.recover_by_id,
            args.recover_all,
        ]
    ):
        parser.error("No action specified")

    try:
        api_key = load_api_key()
    except Exception as e:
        logger.error(f"Failed to load API key: {e}")
        return 1

    if args.scan_existing:
        mapping = extract_request_mapping([PRODUCTION_DIR, STAGING_DIR])
        print(f"\nFound {len(mapping)} existing extractions:")
        for req_id, info in list(mapping.items())[:5]:
            print(f"  {req_id}: {info['folder_name']}")
        if len(mapping) > 5:
            print(f"  ... and {len(mapping) - 5} more")

        mapping_file = LOG_DIR / "existing_mapping.json"
        with open(mapping_file, "w") as f:
            json.dump(mapping, f, indent=2)
        print(f"\nSaved to: {mapping_file}")

    if args.parse_log and args.parse_log.exists():
        entries = parse_extraction_log(args.parse_log)
        print(f"\nFound {len(entries)} entries in log")
        for entry in entries[:5]:
            print(
                f"  {entry.get('request_id', 'N/A')}: {entry.get('output_dir', 'N/A')}"
            )

    if args.report and args.from_log:
        existing = extract_request_mapping([PRODUCTION_DIR, STAGING_DIR])
        log_entries = parse_extraction_log(args.from_log)

        log_pdfs = {e.get("pdf_name") for e in log_entries if e.get("pdf_name")}
        existing_pdfs = {
            info.get("pdf_name") for info in existing.values() if info.get("pdf_name")
        }
        missing_pdfs = log_pdfs - existing_pdfs

        print(f"\n{'=' * 60}")
        print("RECOVERY REPORT")
        print(f"{'=' * 60}")
        print(f"PDFs in log: {len(log_pdfs)}")
        print(f"PDFs extracted: {len(existing_pdfs)}")
        print(f"PDFs missing: {len(missing_pdfs)}")

        if missing_pdfs:
            print(f"\nMissing PDFs (need re-extraction):")
            for pdf_name in sorted(p for p in missing_pdfs if p)[:10]:
                print(f"  - {pdf_name}")
            if len(missing_pdfs) > 10:
                print(f"  ... and {len(missing_pdfs) - 10} more")
        else:
            print("\nAll PDFs from log are present!")

    if args.recover_by_id:
        if not args.check_url:
            logger.error("--check-url required")
            return 1
        success = recover_by_request_id(
            args.recover_by_id, args.check_url, args.output_dir, api_key, args.dry_run
        )
        return 0 if success else 1

    if args.recover_all and args.from_log:
        entries = parse_extraction_log(args.from_log)
        print(f"\nRecovering {len(entries)} extractions...")

        success_count = 0
        for entry in entries:
            req_id = entry.get("request_id")
            check_url = entry.get("check_url")
            if req_id and check_url:
                if recover_by_request_id(
                    req_id, check_url, args.output_dir, api_key, args.dry_run
                ):
                    success_count += 1

        print(f"\nRecovered: {success_count}/{len(entries)}")
        return 0 if success_count == len(entries) else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
