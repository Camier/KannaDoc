# Code Node: Apply Patches (Thesis Blueprint V3)
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

    patch_actions = get_val("patch_actions", [])
    micro_outline = get_val("micro_outline", {})

    if isinstance(micro_outline, str):
        try:
            micro_outline = json.loads(micro_outline)
        except:
            micro_outline = {}

    # patch_actions might be a string from LLM
    if isinstance(patch_actions, str):
        try:
            clean_str = patch_actions
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[1].split("```")[0].strip()

            patch_actions = json.loads(clean_str)
        except:
            pass

    # Apply patches
    if isinstance(patch_actions, list):
        if not isinstance(micro_outline, dict):
            micro_outline = {}
        if "_patches" not in micro_outline:
            micro_outline["_patches"] = []
        micro_outline["_patches"].extend(patch_actions)

    print("####Global variable updated####")
    print(f"micro_outline = {json.dumps(micro_outline)}")
