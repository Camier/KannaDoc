# Code Node: Parse KB Analysis (Thesis Blueprint V3)
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

    kb_analysis_str = get_val("kb_analysis", "")

    # Handle LLM markdown blocks
    if "```json" in kb_analysis_str:
        kb_analysis_str = kb_analysis_str.split("```json")[1].split("```")[0].strip()
    elif "```" in kb_analysis_str:
        kb_analysis_str = kb_analysis_str.split("```")[1].split("```")[0].strip()

    data = {}
    try:
        data = json.loads(kb_analysis_str)
    except (ValueError, SyntaxError, TypeError) as e:
        # If parsing fails, try to clean more or handle as raw string
        print(f"JSON Parse Error: {e}")

    themes_list = data.get("themes", [])
    gaps = data.get("gaps", [])
    key_authors = data.get("key_authors", [])

    print("####Global variable updated####")
    print(f"themes_list = {json.dumps(themes_list)}")
    print(f"themes_count = {len(themes_list)}")
    print(f"gaps = {json.dumps(gaps)}")
    print(f"key_authors = {json.dumps(key_authors)}")
