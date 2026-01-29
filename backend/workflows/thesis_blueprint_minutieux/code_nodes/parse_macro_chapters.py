# Code Node: Parse Macro Chapters (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    macro = get_val("macro_outline", {})
    chapters = macro.get("chapters", [])
    
    print("####Global variable updated####")
    print(f"chapters_list = {json.dumps(chapters)}")
    print(f"chapters_count = {len(chapters)}")
    print(f"chapter_idx = 0")