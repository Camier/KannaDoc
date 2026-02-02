# Code Node: Merge Chapter Micro (Thesis Blueprint V3)
def main(inputs):
    import json
    from ast import literal_eval as parse_val

    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try:
                return parse_val(v)
            except (ValueError, SyntaxError, TypeError):
                return v
        return v

    micro_outline = get_val("micro_outline", {})
    chapter_micro = get_val("chapter_micro", {})

    # Ensure micro_outline is a dict
    if isinstance(micro_outline, str):
        try:
            micro_outline = json.loads(micro_outline)
        except (ValueError, SyntaxError, TypeError):
            micro_outline = {}

    if not isinstance(micro_outline, dict):
        micro_outline = {}

    if "chapters" not in micro_outline:
        micro_outline["chapters"] = []

    # chapter_micro might be a string from LLM
    if isinstance(chapter_micro, str):
        try:
            clean_str = chapter_micro
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[1].split("```")[0].strip()

            chapter_micro = json.loads(clean_str)
        except (ValueError, SyntaxError, TypeError):
            pass

    if isinstance(chapter_micro, dict) and chapter_micro:
        micro_outline["chapters"].append(chapter_micro)
    elif isinstance(chapter_micro, list):
        micro_outline["chapters"].extend(chapter_micro)

    print("####Global variable updated####")
    print(f"micro_outline = {json.dumps(micro_outline)}")
