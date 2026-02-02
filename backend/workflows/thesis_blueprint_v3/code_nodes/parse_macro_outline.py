# Code Node: Parse Macro Outline (Thesis Blueprint V3)
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

    macro_str = get_val("macro_outline", "")

    # Handle possible direct dict/list from get_val
    if isinstance(macro_str, dict):
        data = macro_str
    else:
        # Cleanup markdown
        if "```json" in macro_str:
            macro_str = macro_str.split("```json")[1].split("```")[0].strip()
        elif "```" in macro_str:
            macro_str = macro_str.split("```")[1].split("```")[0].strip()

        data = {}
        try:
            data = json.loads(macro_str)
        except (ValueError, SyntaxError, TypeError) as e:
            print(f"JSON Parse Error: {e}")

    chapters = data.get("chapters", [])

    print("####Global variable updated####")
    print(f"chapters_list = {json.dumps(chapters)}")
    print(f"chapters_count = {len(chapters)}")
