# Code Node: Parse Macro Chapters (Layra Protocol)
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

    macro = get_val("macro_outline", {})
    chapters = macro.get("chapters", [])

    print("####Global variable updated####")
    print(f"chapters_list = {json.dumps(chapters)}")
    print(f"chapters_count = {len(chapters)}")
    print(f"chapter_idx = 0")
