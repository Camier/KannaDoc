# Code Node: Normalize KB Map (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    kb_map = get_val("kb_map", {})
    
    def dedup(lst, key_name):
        seen = set()
        out = []
        for item in lst:
            val = item.get(key_name, "").lower().strip()
            if val and val not in seen:
                seen.add(val)
                out.append(item)
        return out

    if kb_map:
        kb_map["themes"] = dedup(kb_map.get("themes", []), "name")
        kb_map["concepts"] = dedup(kb_map.get("concepts", []), "name")
        kb_map["methods"] = dedup(kb_map.get("methods", []), "name")
        kb_map["sources"] = dedup(kb_map.get("sources", []), "doc_ref")

    print("####Global variable updated####")
    print(f"kb_map = {json.dumps(kb_map)}")