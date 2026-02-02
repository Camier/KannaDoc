#!/usr/bin/env python3
"""CLI script for v2 entity extraction using MinimaxM2.1."""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from lib.entity_extraction import MinimaxExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def process_doc_dir(
    doc_dir: Path,
    extractor: MinimaxExtractor,
    output_dir: Optional[Path] = None,
    chunk_workers: int = 2,
    force: bool = False,
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

    result = extractor.extract_document(
        chunks=chunks,
        doc_id=doc_id,
        max_workers=chunk_workers,
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
        description="Extract entities using MinimaxM2.1 (v2 schema)"
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
        help="Use MiniMax-M2.1-lightning for faster processing",
    )

    args = parser.parse_args()

    extractor = MinimaxExtractor(use_lightning=args.lightning)

    if args.test:
        logger.info(f"Test mode: {args.test}")
        result = extractor.extract_chunk(
            args.test, doc_id="test_doc", chunk_id="test_chunk"
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

    logger.info(f"Found {len(doc_dirs)} documents to process")

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
            ): d
            for d in doc_dirs
        }

        with tqdm(total=len(doc_dirs), desc="Extracting entities v2") as pbar:
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
