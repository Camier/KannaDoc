# Code Node: Apply Scope Changes (Thesis Blueprint V3)
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

    scope_validated = get_val("scope_validated", "")
    requirements = get_val("requirements", {})

    # scope_validated may contain JSON modifications to requirements
    if isinstance(scope_validated, str) and ("{" in scope_validated):
        try:
            clean_str = scope_validated
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[1].split("```")[0].strip()

            updates = json.loads(clean_str)
            if isinstance(updates, dict):
                requirements.update(updates)
        except:
            pass

    print("####Global variable updated####")
    print(f"requirements = {json.dumps(requirements)}")
    print(f"scope_locked = True")
