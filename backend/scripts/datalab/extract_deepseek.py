#!/usr/bin/env python3
"""High-performance async entity extraction using DeepSeek API.

Optimized for maximum throughput with DeepSeek's unique characteristics:
- NO rate limits: can fire 50+ parallel requests
- Automatic context caching: 90% input cost savings on shared system prompts
- 10-minute timeout tolerance for high-load scenarios

Usage:
    # Fast extraction (default: 50 concurrent requests)
    python extract_deepseek.py --input-dir data/extractions --force

    # Adjust concurrency
    python extract_deepseek.py --input-dir data/extractions --concurrency 100

    # Test single text
    python extract_deepseek.py --test "Sceletium contains mesembrine alkaloids"
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tqdm.asyncio import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


async def extract_chunk(
    client: Any,
    doc_id: str,
    chunk_id: str,
    text: str,
    system_prompt: str,
) -> Tuple[str, Dict[str, Any]]:
    """Extract entities from a single chunk using async client."""
    from lib.entity_extraction.prompt import build_messages_v31
    from lib.entity_extraction.extractor import parse_extraction_result

    messages = build_messages_v31(doc_id=doc_id, chunk_id=chunk_id, text=text)

    try:
        response = await client.chat(messages, max_tokens=8192)
        result = parse_extraction_result(response, chunk_id=chunk_id, strict=False)
        return chunk_id, {"success": True, "result": result}
    except Exception as e:
        logger.warning(f"Chunk {chunk_id} failed: {e}")
        return chunk_id, {"success": False, "error": str(e)}


async def process_document(
    client: Any,
    doc_dir: Path,
    system_prompt: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Process all chunks in a document directory."""
    from lib.entity_extraction.schemas import ExtractionResult

    entities_file = doc_dir / "entities.json"
    if entities_file.exists() and not force:
        return {"status": "skipped", "reason": "exists"}

    normalized_file = doc_dir / "normalized.json"
    if not normalized_file.exists():
        return {"status": "skipped", "reason": "no_normalized"}

    try:
        with open(normalized_file) as f:
            data = json.load(f)
            doc_id = data.get("doc_id", doc_dir.name)
            chunks = data.get("chunks", [])
    except Exception as e:
        return {"status": "error", "error": str(e)}

    if not chunks:
        return {"status": "skipped", "reason": "no_chunks"}

    # Create extraction tasks for all chunks
    tasks = []
    for idx, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            chunk_id = chunk.get("chunk_id") or chunk.get("id") or f"chunk_{idx}"
            text = (
                chunk.get("text")
                or chunk.get("chunk_text")
                or chunk.get("content")
                or ""
            )
        else:
            chunk_id = f"chunk_{idx}"
            text = str(chunk)

        tasks.append(extract_chunk(client, doc_id, chunk_id, text, system_prompt))

    # Run all chunks in parallel
    results = await asyncio.gather(*tasks)

    # Merge results
    all_entities = []
    all_relationships = []
    failed_chunks = []

    for chunk_id, result in results:
        if result["success"]:
            extraction = result["result"]
            all_entities.extend(extraction.entities or [])
            all_relationships.extend(extraction.relationships or [])
        else:
            failed_chunks.append({"chunk_id": chunk_id, "error": result["error"]})

    # Save combined result
    combined = ExtractionResult(entities=all_entities, relationships=all_relationships)
    tmp_file = entities_file.with_suffix(".json.tmp")
    with open(tmp_file, "w") as f:
        json.dump(combined.model_dump(), f, indent=2)
    os.replace(tmp_file, entities_file)

    # Log errors if any
    if failed_chunks:
        errors_file = doc_dir / ".errors.jsonl"
        with open(errors_file, "a") as f:
            for err in failed_chunks:
                f.write(json.dumps(err) + "\n")

    return {
        "status": "success",
        "entities": len(all_entities),
        "relationships": len(all_relationships),
        "failed_chunks": len(failed_chunks),
        "total_chunks": len(chunks),
    }


async def run_extraction(
    input_dir: Path,
    concurrency: int = 50,
    force: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run extraction on all documents in input directory."""
    from lib.entity_extraction.deepseek_client import DeepSeekAsyncClient
    from lib.entity_extraction.prompt import SYSTEM_PROMPT_V31

    # Shared system prompt enables DeepSeek context caching (90% input cost savings)
    system_prompt = SYSTEM_PROMPT_V31

    # Find documents to process
    doc_dirs = sorted(
        [
            d
            for d in input_dir.iterdir()
            if d.is_dir() and (d / "normalized.json").exists()
        ]
    )

    if not force:
        doc_dirs = [d for d in doc_dirs if not (d / "entities.json").exists()]

    if limit:
        doc_dirs = doc_dirs[:limit]

    if not doc_dirs:
        logger.info("No documents to process")
        return {"total": 0, "processed": 0}

    logger.info(
        f"Processing {len(doc_dirs)} documents with {concurrency} concurrent requests"
    )

    stats = {"total": len(doc_dirs), "success": 0, "skipped": 0, "error": 0}
    total_entities = 0
    total_relationships = 0

    async with DeepSeekAsyncClient(max_concurrent=concurrency) as client:
        # Process documents with progress bar
        tasks = [
            process_document(client, doc_dir, system_prompt, force)
            for doc_dir in doc_dirs
        ]

        results = []
        for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Extracting"):
            result = await coro
            results.append(result)

            if result["status"] == "success":
                stats["success"] += 1
                total_entities += result.get("entities", 0)
                total_relationships += result.get("relationships", 0)
            elif result["status"] == "skipped":
                stats["skipped"] += 1
            else:
                stats["error"] += 1

    stats["total_entities"] = total_entities
    stats["total_relationships"] = total_relationships
    return stats


async def test_extraction(text: str) -> None:
    """Test extraction on a single text."""
    from lib.entity_extraction.deepseek_client import DeepSeekAsyncClient
    from lib.entity_extraction.prompt import SYSTEM_PROMPT_V31

    system_prompt = SYSTEM_PROMPT_V31

    async with DeepSeekAsyncClient(max_concurrent=1) as client:
        chunk_id, result = await extract_chunk(
            client, "test_doc", "test_chunk", text, system_prompt
        )

        if result["success"]:
            print(json.dumps(result["result"].model_dump(), indent=2))
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="High-performance async entity extraction using DeepSeek API"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/extractions",
        help="Input directory containing document folders",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Max concurrent API requests (default: 50)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing entities.json files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process",
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Test extraction on provided text",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed",
    )

    args = parser.parse_args()

    if args.test:
        asyncio.run(test_extraction(args.test))
        return

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_path}")
        sys.exit(1)

    if args.dry_run:
        doc_dirs = [
            d
            for d in input_path.iterdir()
            if d.is_dir() and (d / "normalized.json").exists()
        ]
        if not args.force:
            doc_dirs = [d for d in doc_dirs if not (d / "entities.json").exists()]
        if args.limit:
            doc_dirs = doc_dirs[: args.limit]
        logger.info(f"Would process {len(doc_dirs)} documents")
        for d in doc_dirs[:10]:
            print(f"  {d.name}")
        if len(doc_dirs) > 10:
            print(f"  ... and {len(doc_dirs) - 10} more")
        return

    stats = asyncio.run(
        run_extraction(
            input_path,
            concurrency=args.concurrency,
            force=args.force,
            limit=args.limit,
        )
    )

    logger.info(f"Extraction complete: {stats}")


if __name__ == "__main__":
    main()
