# Code Node: Accumulate KB Map (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    kb_map = get_val("kb_map", {"themes":[], "concepts":[], "methods":[], "datasets":[], "debates":[], "sources":[]})
    current = get_val("current_axis_result", {})
    
    if current and isinstance(current, dict):
        for key in ["themes_found", "concepts_found", "methods_found", "datasets_found", "debates_found", "candidate_sources"]:
            target = key.replace("_found", "").replace("candidate_", "")
            if key in current:
                kb_map[target].extend(current[key])
                
    print("####Global variable updated####")
    print(f"kb_map = {json.dumps(kb_map)}")