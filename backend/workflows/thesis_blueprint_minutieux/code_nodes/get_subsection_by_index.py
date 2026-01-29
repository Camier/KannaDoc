# Code Node: Get Subsection (Layra Protocol)
def main(inputs):
    import json
    from ast import literal_eval as parse_val
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return parse_val(v)
            except: return v
        return v

    idx = get_val("subsection_idx", 0)
    lst = get_val("subsections_list", [])
    
    print("####Global variable updated####")
    if idx < len(lst):
        print(f"subsection = {json.dumps(lst[idx])}")
    else:
        print("subsection = ''")