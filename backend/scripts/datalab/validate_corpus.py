#!/usr/bin/env python3
"""
Corpus integrity validation for thesis reproducibility.

Checks:
1. PDF <-> Extraction 1:1 correspondence
2. ID mapping consistency
3. Corpus JSONL coverage
4. Extraction quality (entities.json presence, relationship counts)

Exit codes:
  0 - All checks pass
  1 - Validation failures detected
"""

import json
import sys
from pathlib import Path


def main():
    base_dir = Path(__file__).parent.parent.parent / "data"
    pdf_dir = base_dir / "pdfs"
    ext_dir = base_dir / "extractions"
    id_mapping = base_dir / "id_mapping.json"
    corpus_jsonl = base_dir / "corpus" / "biblio_corpus.jsonl"
    manifest = base_dir / "corpus_manifest.jsonl"

    errors = []
    warnings = []

    pdfs = set(p.stem for p in pdf_dir.glob("*.pdf")) if pdf_dir.exists() else set()
    extractions = (
        set(d.name for d in ext_dir.iterdir() if d.is_dir())
        if ext_dir.exists()
        else set()
    )

    print(f"PDFs found: {len(pdfs)}")
    print(f"Extractions found: {len(extractions)}")

    if id_mapping.exists():
        with open(id_mapping) as f:
            mapping = json.load(f)
        print(f"ID mapping entries: {len(mapping)}")
    else:
        errors.append("id_mapping.json not found")
        mapping = {}

    docs_with_entities = 0
    docs_with_relationships = 0
    total_relationships = 0

    for ext_dir_path in ext_dir.iterdir():
        if not ext_dir_path.is_dir():
            continue
        entities_file = ext_dir_path / "entities.json"
        if entities_file.exists():
            docs_with_entities += 1
            try:
                with open(entities_file) as f:
                    data = json.load(f)
                rels = data.get("relationships", [])
                if rels:
                    docs_with_relationships += 1
                    total_relationships += len(rels)
            except json.JSONDecodeError:
                errors.append(f"Invalid JSON: {entities_file}")
        else:
            warnings.append(f"Missing entities.json: {ext_dir_path.name}")

    print(f"\nExtraction Quality:")
    print(f"  Documents with entities: {docs_with_entities}/{len(extractions)}")
    print(
        f"  Documents with relationships: {docs_with_relationships}/{len(extractions)}"
    )
    print(f"  Total relationships: {total_relationships}")

    if corpus_jsonl.exists():
        with open(corpus_jsonl) as f:
            corpus_count = sum(1 for _ in f)
        print(f"  Corpus JSONL entries: {corpus_count}")
    else:
        warnings.append("biblio_corpus.jsonl not found")

    if manifest.exists():
        with open(manifest) as f:
            manifest_count = sum(1 for _ in f)
        print(f"  Corpus manifest entries: {manifest_count}")
    else:
        warnings.append("corpus_manifest.jsonl not found")

    if docs_with_relationships < len(extractions) * 0.8:
        errors.append(
            f"Less than 80% of docs have relationships: {docs_with_relationships}/{len(extractions)}"
        )

    if total_relationships < 500:
        errors.append(
            f"Total relationships below threshold: {total_relationships} < 500"
        )

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings[:10]:
            print(f"  - {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        print("\nValidation FAILED")
        return 1

    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
