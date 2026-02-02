#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def atomic_write_jsonl(path: Path, data: List[Dict[str, Any]]):
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def atomic_write_json(path: Path, data: Any):
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description="Aggregate corpus for ingestion")
    parser.add_argument("--limit", type=int, help="Limit number of documents processed")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/corpus"), help="Output directory"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = Path("data/cache/metadata/paper_catalog.jsonl")
    catalog_map = {}
    if catalog_path.exists():
        logger.info(f"Loading catalog from {catalog_path}")
        with open(catalog_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    catalog_map[entry["paper_id"]] = entry
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding catalog line: {e}")
                    continue
    else:
        logger.error(f"Catalog not found: {catalog_path}")
        sys.exit(1)

    extraction_root = Path("data/extractions/prod_max")
    if not extraction_root.exists():
        logger.error(f"Extraction root not found: {extraction_root}")
        sys.exit(1)

    biblio_corpus = []
    chunks_corpus = []
    images_manifest = set()  # Use set to avoid duplicates across chunks

    matched_paper_ids = set()

    # Use glob to find all request files
    request_files = sorted(list(extraction_root.glob("*/raw/request.json")))
    if args.limit:
        request_files = request_files[: args.limit]

    logger.info(f"Found {len(request_files)} extractions to process")

    for request_path in request_files:
        doc_dir = request_path.parent.parent
        norm_path = doc_dir / "normalized.json"

        if not norm_path.exists():
            logger.warning(f"Normalized file not found for {doc_dir}")
            continue

        try:
            with open(request_path, "r", encoding="utf-8") as f:
                request_data = json.load(f)

            with open(norm_path, "r", encoding="utf-8") as f:
                norm_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading {doc_dir}: {e}")
            continue

        # Extract paper_id from input path stem
        input_path = request_data.get("input")
        if not input_path:
            logger.warning(f"No input path in request.json for {doc_dir}")
            continue

        paper_id = Path(input_path).stem
        catalog_entry = catalog_map.get(paper_id)

        if not catalog_entry:
            logger.warning(
                f"Paper ID '{paper_id}' not found in catalog (doc_id: {norm_data.get('doc_id')})"
            )
            continue

        matched_paper_ids.add(paper_id)

        # Merge metadata (Catalog priority for doi, authors, title, year)
        ext_meta = norm_data.get("metadata", {})
        doc_id = norm_data.get("doc_id")

        merged = {
            "doc_id": doc_id,
            "paper_id": paper_id,
            "citekey": catalog_entry.get("citekey"),
            "title": catalog_entry.get("title") or ext_meta.get("title"),
            "authors": catalog_entry.get("authors") or ext_meta.get("authors"),
            "year": catalog_entry.get("year") or ext_meta.get("publication_year"),
            "doi": catalog_entry.get("doi") or ext_meta.get("doi"),
            "venue": ext_meta.get("venue"),
            "publisher": catalog_entry.get("publisher"),
            "chunk_count": len(norm_data.get("chunks", [])),
            "image_count": len(norm_data.get("images", [])),
            "extraction_path": str(doc_dir),
        }

        # Ensure year is int if possible
        if merged["year"] is not None:
            try:
                merged["year"] = int(merged["year"])
            except (ValueError, TypeError):
                pass

        biblio_corpus.append(merged)

        # Process chunks
        for chunk in norm_data.get("chunks", []):
            page = chunk.get("page_refs", [0])[0] if chunk.get("page_refs") else 0
            block_type = chunk.get("graph_meta", {}).get("block_type", "Unknown")

            # Use block_ids[0] as chunk_id if available for better traceability
            # Falling back to the hash chunk_id if block_ids is empty
            chunk_id = (
                chunk.get("block_ids", [chunk.get("chunk_id")])[0]
                if chunk.get("block_ids")
                else chunk.get("chunk_id")
            )

            chunks_corpus.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "page": page,
                    "block_type": block_type,
                    "text": chunk.get("text"),
                    "html": chunk.get("html"),
                }
            )

        # Collect image paths from images array
        for img in norm_data.get("images", []):
            if img.get("storage_uri"):
                images_manifest.add(img["storage_uri"])

    # Prepare unmatched catalog entries
    unmatched = []
    for paper_id, entry in catalog_map.items():
        if paper_id not in matched_paper_ids:
            unmatched.append({"paper_id": paper_id, "reason": "no_extraction_found"})

    # Write output files
    atomic_write_jsonl(args.output_dir / "biblio_corpus.jsonl", biblio_corpus)
    atomic_write_jsonl(args.output_dir / "chunks_corpus.jsonl", chunks_corpus)
    atomic_write_json(
        args.output_dir / "images_manifest.json", sorted(list(images_manifest))
    )
    atomic_write_jsonl(args.output_dir / "_unmatched.jsonl", unmatched)

    logger.info(f"Aggregation complete.")
    logger.info(f"Matched documents: {len(biblio_corpus)}")
    logger.info(f"Total chunks: {len(chunks_corpus)}")
    logger.info(f"Total images: {len(images_manifest)}")
    logger.info(f"Unmatched catalog entries: {len(unmatched)}")


if __name__ == "__main__":
    main()
