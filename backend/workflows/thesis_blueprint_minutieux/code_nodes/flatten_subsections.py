# Code Node: Flatten Subsections (Layra Protocol)
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

    micro = get_val("micro_outline", {})
    subs = []
    for ch in micro.get("chapters", []):
        for sec in ch.get("sections", []):
            for s in sec.get("subsections", []):
                # Ensure subsection has ID
                s["_ch_title"] = ch.get("title")
                subs.append(s)

    print("####Global variable updated####")
    print(f"subsections_list = {json.dumps(subs)}")
    print(f"subsections_count = {len(subs)}")
    print(f"subsection_idx = 0")
