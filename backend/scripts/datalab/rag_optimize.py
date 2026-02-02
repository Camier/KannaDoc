#!/usr/bin/env python3
"""
RAG Optimization Script for DataLab

Transforms DataLab extraction output into RAG-ready chunks optimized for
vector database storage and retrieval.

Usage:
    python3 scripts/rag_optimize.py /path/to/extraction [--output-dir OUTPUT_DIR]
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from html import unescape
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """HTML parser that extracts plain text while preserving structure."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {"script", "style", "nav", "footer", "header"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.text_parts.append(" ")
        else:
            self.text_parts.append(" ")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.text_parts.append(text)

    def get_text(self) -> str:
        """Extract and clean text from parsed HTML."""
        text = " ".join(self.text_parts)
        # Clean up multiple spaces
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def extract_text_from_html(html: str) -> str:
    """
    Strip HTML tags, decode entities, return plain text.

    Args:
        html: Raw HTML string

    Returns:
        Plain text content with HTML entities decoded
    """
    if not html:
        return ""

    # Decode HTML entities first
    decoded = unescape(html)

    # Extract text using HTML parser
    parser = HTMLTextExtractor()
    parser.feed(decoded)
    text = parser.get_text()

    # Clean up common artifacts
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\xa0\u200b\u200c\u200d\u2060]", " ", text)

    return text.strip()


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def should_skip_block(block: Dict[str, Any]) -> bool:
    """
    Determine if a block should be skipped during aggregation.

    Args:
        block: Block dictionary from extraction

    Returns:
        True if block should be skipped
    """
    block_type = block.get("type", "")

    # Skip structural and non-content blocks
    skip_types = {
        "SectionHeader",
        "PageHeader",
        "PageFooter",
        "PageBreak",
        "Image",
        "Table",
        "Figure",
    }

    if block_type in skip_types:
        return True

    # Skip navigation blocks by text content
    text = extract_text_from_html(block.get("html", ""))
    if not text or len(text) < 50:
        return True

    # Skip common navigation patterns
    nav_patterns = [
        r"^\s*(navigation|menu|contents|index)\s*$",
        r"^\s*(next|previous|back|home)\s*$",
        r"^\s*\d+\s*$",  # Just numbers
    ]

    for pattern in nav_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    return False


def get_section_key(block: Dict[str, Any]) -> tuple:
    """
    Extract section hierarchy key for grouping blocks.

    Args:
        block: Block dictionary

    Returns:
        Tuple representing section hierarchy
    """
    hierarchy = block.get("section_hierarchy", {})

    # Build key from hierarchy levels
    levels = []
    for i in range(1, 6):  # Support up to level 5
        level_key = f"level_{i}"
        if level_key in hierarchy:
            levels.append(hierarchy[level_key])
        else:
            break

    return tuple(levels)


def aggregate_chunks_by_section(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group adjacent Text chunks within same section_hierarchy.
    Target: 500-1000 characters. Skip navigation blocks.

    Args:
        chunks: List of chunk dictionaries from extraction

    Returns:
        List of aggregated chunk dictionaries
    """
    if not chunks:
        return []

    # Filter out blocks to skip
    filtered_chunks = [c for c in chunks if not should_skip_block(c)]

    if not filtered_chunks:
        return []

    aggregated = []
    current_group: List[Dict[str, Any]] = []
    current_text_length = 0
    current_section = None

    for chunk in filtered_chunks:
        section_key = get_section_key(chunk)
        chunk_text = extract_text_from_html(chunk.get("html", ""))
        chunk_length = len(chunk_text)

        # Check if we should start a new group
        need_new_group = (
            current_section is None
            or section_key != current_section
            or current_text_length + chunk_length > 1000
            or (current_text_length >= 500 and current_text_length + chunk_length > 800)
        )

        if need_new_group:
            # Save current group if it meets minimum size
            if current_group and current_text_length >= 50:
                aggregated.append(_merge_group(current_group))

            # Start new group
            current_group = [chunk]
            current_text_length = chunk_length
            current_section = section_key
        else:
            # Add to current group
            current_group.append(chunk)
            current_text_length += chunk_length

    # Don't forget the last group
    if current_group and current_text_length >= 50:
        aggregated.append(_merge_group(current_group))

    return aggregated


def _merge_group(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge a group of chunks into a single aggregated chunk.

    Args:
        group: List of chunks to merge

    Returns:
        Merged chunk dictionary
    """
    if not group:
        raise ValueError("Cannot merge empty group")

    # Use first chunk as base for metadata
    base = group[0]

    # Combine HTML and text
    combined_html = " ".join(c.get("html", "") for c in group)
    combined_text = extract_text_from_html(combined_html)

    # Aggregate section hierarchy
    merged_hierarchy = {}
    for chunk in group:
        hierarchy = chunk.get("section_hierarchy", {})
        for key, value in hierarchy.items():
            if value and value.strip():
                merged_hierarchy[key] = value

    # Collect all entities
    all_entities = set()
    for chunk in group:
        entities = chunk.get("key_entities", [])
        if isinstance(entities, list):
            all_entities.update(e for e in entities if e and isinstance(e, str))

    # Determine page range
    pages: List[int] = [p for p in (c.get("page") for c in group) if p is not None]
    page = pages[0] if pages else None
    page_range = None
    if pages:
        min_page = min(pages)
        max_page = max(pages)
        if min_page == max_page:
            page_range = str(min_page)
        else:
            page_range = f"{min_page}-{max_page}"

    return {
        "html": combined_html,
        "text": combined_text,
        "page": page,
        "page_range": page_range,
        "section_hierarchy": merged_hierarchy,
        "key_entities": sorted(list(all_entities)),
        "chunk_type": "aggregated",
        "block_count": len(group),
        "char_count": len(combined_text),
    }


def merge_document_metadata(extraction_path: Path) -> Dict[str, Any]:
    """
    Load extraction.json and return document metadata.

    Args:
        extraction_path: Path to extraction directory

    Returns:
        Document metadata dictionary
    """
    # Check for extracted/extraction.json (newer format) or extraction.json (older)
    extraction_file = extraction_path / "extracted" / "extraction.json"
    if not extraction_file.exists():
        extraction_file = extraction_path / "extraction.json"

    if not extraction_file.exists():
        raise FileNotFoundError(f"Extraction file not found: {extraction_file}")

    with open(extraction_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract document-level metadata
    source_file = data.get("source_file", "")

    # Extract paper name from source_file or directory name
    # Directory format: YYYYMMDD_HHMMSS_HASH_<ORIGINAL_NAME>
    if source_file:
        paper_name = Path(source_file).stem
    else:
        dir_name = extraction_path.name
        # Strip timestamp and hash prefix: 20260131_013846_0f8c4d23_<name>
        parts = dir_name.split("_", 3)
        paper_name = parts[3] if len(parts) > 3 else dir_name

    metadata = {
        "doc_id": data.get("doc_id") or compute_hash(extraction_path.name),
        "paper_name": paper_name,
        "doc_title": data.get("title", ""),
        "authors": data.get("authors", []),
        "year": data.get("year"),
        "doi": data.get("doi", ""),
        "source_file": source_file,
        "extraction_date": data.get("extraction_date", ""),
        "total_pages": data.get("total_pages"),
        "file_hash": data.get("file_hash", ""),
    }

    return metadata


def create_enriched_chunk(
    aggregated_chunk: Dict[str, Any], metadata: Dict[str, Any], chunk_index: int
) -> Dict[str, Any]:
    """
    Create RAG-ready chunk with all fields.

    Args:
        aggregated_chunk: Merged chunk from aggregation
        metadata: Document metadata
        chunk_index: Index of this chunk in the document

    Returns:
        Enriched chunk ready for RAG
    """
    # Get section name from hierarchy
    hierarchy = aggregated_chunk.get("section_hierarchy", {})
    section = hierarchy.get("level_1", hierarchy.get("level_0", ""))

    # Create unique chunk ID
    text_content = aggregated_chunk.get("text", "")
    chunk_suffix = f"_chunk{chunk_index}"
    chunk_id = compute_hash(metadata["doc_id"] + chunk_suffix)

    # Extract page information for Milvus compatibility
    page = aggregated_chunk.get("page", 0)
    page_range = aggregated_chunk.get("page_range")
    if page_range and len(page_range) >= 2:
        page_start = page_range[0]
        page_end = page_range[1]
    else:
        page_start = page if page is not None else 0
        page_end = page_start

    # Build final chunk structure
    # Includes both doc_id (legacy) and paper_name (Milvus) for compatibility
    enriched = {
        "id": chunk_id,
        "text": text_content,
        "html": aggregated_chunk.get("html", ""),
        "doc_id": metadata["doc_id"],
        "paper_name": metadata["paper_name"],
        "doc_title": metadata["doc_title"],
        "authors": metadata["authors"],
        "year": metadata["year"],
        "doi": metadata["doi"],
        "page": page,
        "page_start": page_start,  # Milvus compatibility
        "page_end": page_end,  # Milvus compatibility
        "page_range": page_range,
        "section": section,
        "section_hierarchy": hierarchy,
        "key_entities": aggregated_chunk.get("key_entities", []),
        "chunk_type": aggregated_chunk.get("chunk_type", "aggregated"),
        "char_count": aggregated_chunk.get("char_count", len(text_content)),
        "block_count": aggregated_chunk.get("block_count", 1),
    }

    return enriched


def load_chunks_from_extraction(extraction_path: Path) -> List[Dict[str, Any]]:
    """
    Load all chunks from extraction directory.

    DataLab stores chunks in rag/chunks.jsonl as line-delimited JSON.

    Args:
        extraction_path: Path to extraction directory

    Returns:
        List of chunk dictionaries
    """
    # DataLab stores chunks in rag/chunks.jsonl
    chunks_file = extraction_path / "rag" / "chunks.jsonl"

    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                chunks.append(chunk)
            except json.JSONDecodeError as e:
                logger.warning(f"[WARN] Failed to parse line {line_num}: {e}")

    if not chunks:
        logger.warning(f"[WARN] No chunks found in {chunks_file}")

    return chunks


def validate_chunk(chunk: Dict[str, Any]) -> bool:
    """
    Validate that a chunk meets minimum requirements.

    Args:
        chunk: Chunk dictionary to validate

    Returns:
        True if chunk is valid
    """
    required_fields = ["id", "text", "doc_id", "doc_title"]

    for field in required_fields:
        if field not in chunk:
            logger.error(f"[ERROR] Missing required field: {field}")
            return False

    if len(chunk.get("text", "")) < 50:
        logger.warning(
            f"[WARN] Chunk {chunk.get('id')} too short: {len(chunk['text'])} chars"
        )
        return False

    return True


def write_jsonl(chunks: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write chunks to JSONL file.

    Args:
        chunks: List of chunk dictionaries
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            if validate_chunk(chunk):
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                valid_count += 1

    logger.info(f"[OK] Wrote {valid_count} valid chunks to {output_path}")


def print_statistics(
    original_count: int, aggregated_count: int, chunks: List[Dict[str, Any]]
) -> None:
    """
    Print optimization statistics.

    Args:
        original_count: Number of original chunks
        aggregated_count: Number of aggregated chunks
        chunks: List of final enriched chunks
    """
    total_chars = sum(c.get("char_count", 0) for c in chunks)
    avg_chars = total_chars / len(chunks) if chunks else 0

    char_counts = [c.get("char_count", 0) for c in chunks]
    min_chars = min(char_counts) if char_counts else 0
    max_chars = max(char_counts) if char_counts else 0

    target_min = sum(1 for c in chunks if 500 <= c.get("char_count", 0) <= 1000)

    logger.info("\n" + "=" * 60)
    logger.info("RAG OPTIMIZATION STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Original chunks:     {original_count}")
    logger.info(f"Optimized chunks:    {aggregated_count}")
    logger.info(
        f"Reduction:           {((1 - aggregated_count / original_count) * 100):.1f}%"
    )
    logger.info(f"")
    logger.info(f"Total characters:    {total_chars:,}")
    logger.info(f"Avg chunk size:      {avg_chars:.0f} chars")
    logger.info(f"Min chunk size:      {min_chars} chars")
    logger.info(f"Max chunk size:      {max_chars} chars")
    logger.info(
        f"In target range:     {target_min}/{aggregated_count} ({(target_min / aggregated_count * 100):.1f}%)"
    )
    logger.info("=" * 60)


def process_extraction(
    extraction_path: Path, output_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Process a single extraction directory.

    Args:
        extraction_path: Path to extraction directory
        output_dir: Optional output directory (default: rag_optimized/)

    Returns:
        Path to output file
    """
    logger.info(f"\n[START] Processing: {extraction_path.name}")

    # Validate input
    if not extraction_path.exists():
        raise FileNotFoundError(f"Extraction directory not found: {extraction_path}")

    # Set output directory
    if output_dir is None:
        output_dir = extraction_path.parent / "rag_optimized"

    # Load extraction data
    logger.info("[LOAD] Loading extraction data...")
    metadata = merge_document_metadata(extraction_path)
    original_chunks = load_chunks_from_extraction(extraction_path)

    if not original_chunks:
        logger.warning(f"[SKIP] No chunks to process in {extraction_path}")
        return None

    logger.info(f"[OK] Loaded {len(original_chunks)} chunks")

    # Aggregate chunks
    logger.info("[AGGREGATE] Grouping chunks by section...")
    aggregated_chunks = aggregate_chunks_by_section(original_chunks)
    logger.info(f"[OK] Created {len(aggregated_chunks)} aggregated chunks")

    # Enrich with metadata
    logger.info("[ENRICH] Adding document metadata...")
    enriched_chunks = []
    for idx, agg_chunk in enumerate(aggregated_chunks):
        enriched = create_enriched_chunk(agg_chunk, metadata, idx)
        enriched_chunks.append(enriched)

    logger.info(f"[OK] Enriched {len(enriched_chunks)} chunks")

    # Write output
    output_file = output_dir / "chunks_for_milvus.jsonl"
    logger.info(f"[WRITE] Writing to: {output_file}")
    write_jsonl(enriched_chunks, output_file)

    # Print statistics
    print_statistics(len(original_chunks), len(aggregated_chunks), enriched_chunks)

    logger.info(f"\n[DONE] Output: {output_file}")
    return output_file


def process_batch(extraction_dir: Path, output_path: Path, quiet: bool = False) -> int:
    """
    Process all extraction directories and aggregate into single JSONL.

    Args:
        extraction_dir: Parent directory containing all extraction subdirs
        output_path: Output JSONL file path
        quiet: Suppress per-document output

    Returns:
        Total chunks written
    """
    subdirs = sorted([d for d in extraction_dir.iterdir() if d.is_dir()])
    if not subdirs:
        logger.error(f"[ERROR] No extraction directories found in {extraction_dir}")
        return 0

    logger.info(f"[BATCH] Processing {len(subdirs)} extractions...")

    all_chunks = []
    success_count = 0
    failed_count = 0

    for subdir in subdirs:
        try:
            if not quiet:
                logger.info(f"[PROC] {subdir.name}")

            metadata = merge_document_metadata(subdir)
            original_chunks = load_chunks_from_extraction(subdir)

            if not original_chunks:
                if not quiet:
                    logger.warning(f"[SKIP] No chunks: {subdir.name}")
                continue

            aggregated_chunks = aggregate_chunks_by_section(original_chunks)
            for idx, agg_chunk in enumerate(aggregated_chunks):
                enriched = create_enriched_chunk(agg_chunk, metadata, idx)
                if validate_chunk(enriched):
                    all_chunks.append(enriched)

            success_count += 1
        except Exception as e:
            failed_count += 1
            logger.warning(f"[FAIL] {subdir.name}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    logger.info(f"\n[BATCH COMPLETE]")
    logger.info(f"  Processed: {success_count}/{len(subdirs)} extractions")
    logger.info(f"  Failed: {failed_count}")
    logger.info(f"  Total chunks: {len(all_chunks)}")
    logger.info(f"  Output: {output_path}")

    return len(all_chunks)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Transform DataLab extraction output into RAG-ready chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s datextract/20240101_abc123_document
  %(prog)s datextract/TIMESTAMP_UUID_docname --output-dir custom_output
  %(prog)s data/FULL_RAG_EXTRACTION --batch --output data/rag/all_chunks.jsonl
        """,
    )

    parser.add_argument(
        "extraction_path",
        type=Path,
        help="Path to extraction directory (single) or parent directory (batch mode)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for optimized chunks (default: rag_optimized/)",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all subdirectories and aggregate into single output",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path for batch mode (default: <extraction_path>/all_chunks.jsonl)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-document output in batch mode",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.batch:
            output_path = args.output or (args.extraction_path / "all_chunks.jsonl")
            count = process_batch(args.extraction_path, output_path, args.quiet)
            return 0 if count > 0 else 1
        else:
            output_path = process_extraction(args.extraction_path, args.output_dir)
            return 0 if output_path else 1
    except Exception as e:
        logger.error(f"\n[ERROR] {type(e).__name__}: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
