# Code Node: Append Micro (Layra Protocol)
import sys

sys.path.insert(0, "/LAB/@thesis/layra/backend")
from workflows.utils.safe_parse import safe_parse


def main(inputs):
    import json

    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            return safe_parse(v)
        return v

    micro = get_val("micro_outline", {"chapters": []})
    new_ch = get_val("micro_chapter", {})

    if new_ch and isinstance(new_ch, dict):
        if "chapter" in new_ch:
            new_ch = new_ch["chapter"]
        micro["chapters"].append(new_ch)

    print("####Global variable updated####")
    print(f"micro_outline = {json.dumps(micro)}")
