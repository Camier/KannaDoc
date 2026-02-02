# Code Node: Merge Sources (Layra Protocol)
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
    found = get_val("found_sources", {})

    sid = found.get("subsection_id")
    srcs = found.get("candidate_sources", [])

    if sid:
        for ch in micro.get("chapters", []):
            for sec in ch.get("sections", []):
                for sub in sec.get("subsections", []):
                    if sub.get("subsection_id") == sid:
                        sub["candidate_sources"] = srcs
                        break

    print("####Global variable updated####")
    print(f"micro_outline = {json.dumps(micro)}")
