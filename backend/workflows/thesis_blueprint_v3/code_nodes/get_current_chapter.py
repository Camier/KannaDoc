# Code Node: Get Current Chapter (Thesis Blueprint V3)
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

    idx = get_val("chapter_idx", 0)
    lst = get_val("chapters_list", [])

    # Ensure lst is a list
    if not isinstance(lst, list):
        try:
            lst = json.loads(lst) if isinstance(lst, str) else []
        except (ValueError, SyntaxError, TypeError):
            lst = []

    print("####Global variable updated####")
    if isinstance(lst, list) and idx < len(lst):
        print(f"current_chapter = {json.dumps(lst[idx])}")
    else:
        print("current_chapter = ''")
