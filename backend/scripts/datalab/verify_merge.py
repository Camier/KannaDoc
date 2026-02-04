import json
from pathlib import Path
import sys


def verify_merge():
    layra_data = Path("/LAB/@thesis/layra/backend/data")
    id_mapping_file = layra_data / "id_mapping.json"
    extractions_dir = layra_data / "extractions"

    if not id_mapping_file.exists():
        print(f"FAIL: {id_mapping_file} not found")
        return

    with open(id_mapping_file) as f:
        mapping = json.load(f)

    mapping_doc_ids = {item["doc_id"] for item in mapping}
    print(f"Loaded {len(mapping)} entries from id_mapping.json")

    if not extractions_dir.exists():
        print(f"FAIL: {extractions_dir} not found")
        return

    extraction_dirs = [d for d in extractions_dir.iterdir() if d.is_dir()]
    print(f"Found {len(extraction_dirs)} extraction directories in LAYRA")

    matched_count = 0
    missing_ids = []

    for d in extraction_dirs:
        entities_file = d / "entities.json"
        if not entities_file.exists():
            print(f"WARNING: No entities.json in {d.name}")
            continue

        try:
            with open(entities_file) as f:
                data = json.load(f)
                doc_id = data.get("doc_id")

                if doc_id in mapping_doc_ids:
                    matched_count += 1
                else:
                    print(
                        f"WARNING: doc_id {doc_id} from {d.name} NOT FOUND in mapping"
                    )
                    missing_ids.append(doc_id)

        except Exception as e:
            print(f"ERROR reading {entities_file}: {e}")

    print("-" * 30)
    print(f"Verification Results:")
    print(f"Total Mapping Entries: {len(mapping)}")
    print(f"Total Extraction Dirs: {len(extraction_dirs)}")
    print(f"Matched Documents:     {matched_count}")

    if matched_count == len(mapping):
        print("SUCCESS: All mapped documents have linked extractions.")
    else:
        print(f"FAILURE: Only {matched_count}/{len(mapping)} matched.")


if __name__ == "__main__":
    verify_merge()
