#!/usr/bin/env python3
"""Create ID mapping from filesystem (no MongoDB needed)."""

import hashlib
import json
import os
from pathlib import Path


def compute_doc_id(filename: str) -> str:
    """Match DataLab's doc_id computation."""
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()


def main():
    datalab_pdf_dir = Path("/LAB/@thesis/datalab/ALL_FLAT")
    if not datalab_pdf_dir.exists():
        print(f"Error: DataLab PDF directory not found: {datalab_pdf_dir}")
        return

    datalab_pdfs = sorted(datalab_pdf_dir.glob("*.pdf"))

    layra_pdf_dir = Path("/LAB/@thesis/layra/backend/literature/corpus")

    mappings = []
    for pdf in datalab_pdfs:
        filename = pdf.name
        doc_id = compute_doc_id(filename)

        layra_pdf = layra_pdf_dir / filename
        file_id = pdf.stem

        mappings.append(
            {
                "filename": filename,
                "doc_id": doc_id,
                "file_id": file_id,
                "datalab_path": str(pdf),
                "layra_exists": layra_pdf.exists() if layra_pdf_dir.exists() else False,
            }
        )

    output_path = Path("/LAB/@thesis/layra/backend/data/id_mapping.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(mappings, f, indent=2)

    print(f"Created {len(mappings)} mappings at {output_path}")

    matched = sum(1 for m in mappings if m.get("layra_exists"))
    print(f"Matched in LAYRA: {matched}/{len(mappings)}")


if __name__ == "__main__":
    main()
