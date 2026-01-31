# Code Node: Coverage Scoring (Thesis Blueprint V3)
def main(inputs):
    import json
    from ast import literal_eval as parse_val

    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try:
                return parse_val(v)
            except:
                return v
        return v

    micro_outline = get_val("micro_outline", {})
    requirements = get_val("requirements", {})

    if isinstance(micro_outline, str):
        try:
            micro_outline = json.loads(micro_outline)
        except:
            micro_outline = {}

    chapters = micro_outline.get("chapters", [])
    num_chapters = len(chapters)

    # Simple coverage logic for V3
    score = min(1.0, (num_chapters * 0.15))  # Arbitrary logic for testing

    coverage = {
        "score": score,
        "details": f"Analyzed {num_chapters} chapters.",
        "status": "sufficient" if score >= 0.6 else "insufficient",
    }

    print("####Global variable updated####")
    print(f"coverage = {json.dumps(coverage)}")
