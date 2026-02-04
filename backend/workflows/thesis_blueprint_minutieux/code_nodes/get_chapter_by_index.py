# Code Node: Get Chapter By Index (Layra Protocol)
def main(inputs):
    import json
    from ast import literal_eval as parse_val

    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try:
                return parse_val(v)
            except (ValueError, SyntaxError):
                return v
        return v

    idx = get_val("chapter_idx", 0)
    lst = get_val("chapters_list", [])

    print("####Global variable updated####")
    if idx < len(lst):
        print(f"chapter = {json.dumps(lst[idx])}")
    else:
        print("chapter = ''")
