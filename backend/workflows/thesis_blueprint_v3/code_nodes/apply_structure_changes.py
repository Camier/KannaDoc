# Code Node: Apply Structure Changes (Thesis Blueprint V3)
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

    structure_changes = get_val("structure_changes", "")
    macro_outline = get_val("macro_outline", {})

    if isinstance(macro_outline, str):
        try:
            macro_outline = json.loads(macro_outline)
        except (ValueError, SyntaxError, TypeError):
            macro_outline = {"chapters": []}

    # Apply structure changes if any
    if isinstance(structure_changes, str) and (
        "{" in structure_changes or "[" in structure_changes
    ):
        try:
            clean_str = structure_changes
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[1].split("```")[0].strip()

            updates = json.loads(clean_str)
            if isinstance(updates, dict):
                if "chapters" in updates:
                    macro_outline["chapters"] = updates["chapters"]
                else:
                    macro_outline.update(updates)
            elif isinstance(updates, list):
                macro_outline["chapters"] = updates
        except (ValueError, SyntaxError, TypeError):
            pass

    chapters = macro_outline.get("chapters", [])

    print("####Global variable updated####")
    print(f"macro_outline = {json.dumps(macro_outline)}")
    print(f"chapters_list = {json.dumps(chapters)}")
