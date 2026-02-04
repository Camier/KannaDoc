#!/usr/bin/env python3
"""CLI script for v2 entity extraction using MinimaxM2.1 or Zhipu GLM-4."""

import argparse
import time
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from tqdm import tqdm

from lib.entity_extraction import V31Extractor
from lib.entity_extraction.clients import ZhipuChatClient, MinimaxChatClient
from lib.entity_extraction.schemas import ExtractionResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def get_extractor(
    provider: str,
    model: Optional[str] = None,
    use_lightning: bool = False,
) -> V31Extractor:
    """Create a V31Extractor wired to the appropriate chat client."""
    if provider == "zhipu":
        client = ZhipuChatClient(model=model or "glm-4.7-flash")
        default_model = model or "glm-4.7-flash"
    else:
        client = MinimaxChatClient(model=model or "MiniMax-M2.1")
        default_model = model or "MiniMax-M2.1"

    logger.info(f"Using V31Extractor with provider={provider}, model={default_model}")
    return V31Extractor(client=client, model=default_model, max_tokens=8192)


def _chunk_to_id_text(chunk: Union[Dict[str, Any], str], idx: int) -> tuple:
    """Infer chunk_id and text from a chunk entry.

    Supports chunk entries shaped as dicts with common keys or raw strings.
    """
    cid = None
    text = None
    if isinstance(chunk, dict):
        cid = chunk.get("chunk_id") or chunk.get("id") or f"chunk_{idx}"
        text = (
            chunk.get("text") or chunk.get("chunk_text") or chunk.get("content") or ""
        )
    else:
        cid = f"chunk_{idx}"
        text = str(chunk)
    return cid, text


def process_doc_dir(
    doc_dir: Path,
    extractor: V31Extractor,
    output_dir: Optional[Path] = None,
    chunk_workers: int = 2,
    force: bool = False,
    chunk_delay: int = 0,
) -> bool:
    target_dir = output_dir or doc_dir
    entities_file = target_dir / "entities.json"

    if entities_file.exists() and not force:
        logger.info(f"Skipping {doc_dir.name} - entities.json already exists")
        return True

    normalized_file = doc_dir / "normalized.json"
    if not normalized_file.exists():
        logger.warning(f"Skipping {doc_dir.name} - normalized.json not found")
        return False

    try:
        with open(normalized_file) as f:
            data = json.load(f)
            doc_id = data.get("doc_id", doc_dir.name)
            chunks = data.get("chunks", [])
    except Exception as e:
        logger.error(f"Failed to load {normalized_file}: {e}")
        return False

    if not chunks:
        logger.warning(f"No chunks found in {normalized_file}")
        return False

    # Chunk processing - use sequential mode if chunk_delay > 0 for rate limiting
    combined_entities: List[Any] = []
    combined_relationships: List[Any] = []

    def _process_chunk(idx: int, chunk: Union[Dict[str, Any], str]):
        chunk_id, text = _chunk_to_id_text(chunk, idx)
        return extractor.extract(doc_id=doc_id, chunk_id=chunk_id, text=text)

    results: List[ExtractionResult] = []

    if chunk_delay and chunk_delay > 0:
        # Sequential processing with delays for rate limiting
        for i, c in enumerate(chunks):
            try:
                result = _process_chunk(i, c)
                results.append(result)
                if i < len(chunks) - 1:  # Don't delay after last chunk
                    time.sleep(chunk_delay)
            except Exception as e:
                logger.error(f"Chunk {i} failed for {doc_id}: {e}")
    else:
        # Parallel processing when no delay needed
        with ThreadPoolExecutor(max_workers=chunk_workers) as ex:
            futures = [ex.submit(_process_chunk, i, c) for i, c in enumerate(chunks)]
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    logger.error(f"Chunk processing failed for {doc_id}: {e}")

    # Merge per-chunk results into a single document result
    for r in results:
        if isinstance(r, ExtractionResult):
            combined_entities.extend(r.entities or [])
            combined_relationships.extend(r.relationships or [])
        else:
            # Defensive: if a raw dict sneaks in, try to merge
            ent = getattr(r, "entities", [])
            rel = getattr(r, "relationships", [])
            combined_entities.extend(ent or [])
            combined_relationships.extend(rel or [])

    result = ExtractionResult(
        entities=combined_entities,
        relationships=combined_relationships,
    )

    tmp_file = entities_file.with_suffix(".json.tmp")
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(tmp_file, "w") as f:
        json.dump(result.model_dump(), f, indent=2)
    os.replace(tmp_file, entities_file)

    logger.info(f"Finished {doc_dir.name}: {len(result.entities)} entities found")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract entities using MinimaxM2.1 or Zhipu GLM-4 (v2 schema)"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=False,
        default="data/PROD_EXTRACTION_V2",
        help="Input directory containing document folders with normalized.json",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["minimax", "zhipu"],
        default="zhipu",
        help="LLM provider for extraction (default: zhipu)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model to use (zhipu: glm-4-plus, glm-4-flash, glm-4-air; minimax: MiniMax-M2.1)",
    )
    parser.add_argument(
        "--doc-workers",
        type=int,
        default=4,
        help="Parallel document workers (default: 4)",
    )
    parser.add_argument(
        "--chunk-workers",
        type=int,
        default=2,
        help="Parallel chunk workers per doc (default: 2)",
    )
    parser.add_argument(
        "--chunk-delay",
        type=int,
        default=0,
        help="Seconds to wait between chunk extractions",
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing entities.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process",
    )
    parser.add_argument(
        "--lightning",
        action="store_true",
        help="Use MiniMax-M2.1-lightning for faster processing (minimax only)",
    )

    args = parser.parse_args()

    # Create extractor based on provider selection
    extractor = get_extractor(
        provider=args.provider,
        model=args.model,
        use_lightning=args.lightning,
    )

    if args.test:
        logger.info(f"Test mode with {args.provider}: {args.test}")
        result = extractor.extract(
            doc_id="test_doc", chunk_id="test_chunk", text=args.test
        )
        print(json.dumps(result.model_dump(), indent=2))
        return

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_path}")
        sys.exit(1)

    doc_dirs = sorted(
        [
            d
            for d in input_path.iterdir()
            if d.is_dir() and (d / "normalized.json").exists()
        ]
    )

    if not args.force:
        doc_dirs = [d for d in doc_dirs if not (d / "entities.json").exists()]

    if args.limit:
        doc_dirs = doc_dirs[: args.limit]

    if args.dry_run:
        logger.info(f"Dry run: would process {len(doc_dirs)} documents")

        for d in doc_dirs:
            print(f"  {d.name}")
        return

    logger.info(f"Found {len(doc_dirs)} documents to process with {args.provider}")

    output_base = Path(args.output_dir) if args.output_dir else None

    with ThreadPoolExecutor(max_workers=args.doc_workers) as executor:
        futures = {
            executor.submit(
                process_doc_dir,
                d,
                extractor,
                output_base / d.name if output_base else None,
                args.chunk_workers,
                args.force,
                args.chunk_delay,
            ): d
            for d in doc_dirs
        }

        with tqdm(
            total=len(doc_dirs), desc=f"Extracting entities ({args.provider})"
        ) as pbar:
            for future in as_completed(futures):
                d = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected error for {d.name}: {e}")
                finally:
                    pbar.update(1)


if __name__ == "__main__":
    main()
