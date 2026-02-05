#!/usr/bin/env python3
"""Migration script for v1 to v2 entity extraction format."""

# ============================================================================
# DEPRECATED - LEGACY V1→V2 MIGRATION SCRIPT
# ============================================================================
# This script was used to migrate entities from V1 to V2 schema format.
# The current schema is V3.1 (17 entity types, 16 relationships).
#
# For new entity extractions, use:
#   - extract_deepseek.py (recommended, async high-throughput)
#   - extract_entities_v2.py (sync CLI for testing/debugging)
#
# This script is preserved for historical reference only.
# ============================================================================

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.entity_extraction.schemas import Entity, ExtractionResultV2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    "Plant": "Taxon",
    "Compound": "Compound",
    "Effect": "PharmEffect",
    "Disease": "Indication",
    "Dosage": "Concentration",
    "Mechanism": "Mechanism",
    "TraditionalUse": "TraditionalUse",
    "Population": "Study",
}


def migrate_file(
    entities_file: Path,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    backup_file = entities_file.with_suffix(".v1.bak")

    try:
        with open(entities_file, "r") as f:
            data = json.load(f)
            if data.get("schema_version") == "2.0" and not force:
                logger.info(f"Skipping {entities_file.parent.name} - already v2")
                return True
    except Exception:
        pass

    if not entities_file.exists():
        logger.warning(f"File not found: {entities_file}")
        return False

    try:
        with open(entities_file, "r") as f:
            v1_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {entities_file}: {e}")
        return False

    doc_id = v1_data.get("doc_id", "")
    chunk_entities_v1 = v1_data.get("chunk_entities", [])

    new_entities: List[Entity] = []
    entity_id_counter = 1

    for chunk_entry in chunk_entities_v1:
        chunk_id = chunk_entry.get("chunk_id", "")
        entities_v1 = chunk_entry.get("entities", [])

        for ent_v1 in entities_v1:
            old_type = ent_v1.get("type") or ent_v1.get("entity_type")
            name = ent_v1.get("name") or ent_v1.get("entity_name", "")
            context = ent_v1.get("context", "")

            if old_type == "Legal":
                continue

            new_type = TYPE_MAPPING.get(old_type)
            if not new_type:
                logger.debug(f"Unknown type '{old_type}', skipping")
                continue

            ent_id = f"ent_{entity_id_counter:03d}"
            entity_id_counter += 1

            new_entities.append(
                Entity(
                    id=ent_id,
                    type=new_type,
                    name=name,
                    attributes={"context": context},
                    source_chunk_ids=[chunk_id] if chunk_id else [],
                )
            )

    result = ExtractionResultV2(
        doc_id=doc_id,
        extracted_at=v1_data.get("extraction_date")
        or datetime.now(timezone.utc).isoformat(),
        extractor=v1_data.get("model", "legacy-migration"),
        entities=new_entities,
        relationships=[],
        metadata={
            "migration_date": datetime.now(timezone.utc).isoformat(),
            "original_file": str(entities_file.name),
        },
    )

    if dry_run:
        logger.info(
            f"Dry run: would migrate {entities_file.parent.name} ({len(new_entities)} entities)"
        )
        return True

    if not backup_file.exists() or force:
        os.rename(entities_file, backup_file)

    tmp_file = entities_file.with_suffix(".json.tmp")
    with open(tmp_file, "w") as f:
        json.dump(result.model_dump(), f, indent=2)
    os.replace(tmp_file, entities_file)

    logger.info(f"Migrated {entities_file.parent.name}: {len(new_entities)} entities")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate entities.json from v1 to v2 format"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing document subdirectories with entities.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite even if v2 exists",
    )

    args = parser.parse_args()

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_path}")
        sys.exit(1)

    entities_files = sorted(list(input_path.glob("*/entities.json")))

    if not entities_files:
        logger.info("No entities.json files found to migrate")
        return

    migrated = 0
    skipped = 0
    errors = 0

    for ent_file in entities_files:
        try:
            success = migrate_file(ent_file, args.dry_run, args.force)
            if success:
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Error migrating {ent_file}: {e}")
            errors += 1

    logger.info(f"Summary: {migrated} migrated, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
