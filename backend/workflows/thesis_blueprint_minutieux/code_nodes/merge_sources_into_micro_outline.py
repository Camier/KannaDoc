# Code Node: Merge Sources (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    micro = get_val("micro_outline", {})
    found = get_val("found_sources", {})
    
    sid = found.get("subsection_id")
    srcs = found.get("candidate_sources", [])
    
    if sid:
        for ch in micro.get("chapters", []):
            for sec in ch.get("sections", []):
                for sub in sec.get("subsections", []):
                    if sub.get("subsection_id") == sid:
                        sub["candidate_sources"] = srcs
                        break
                        
    print("####Global variable updated####")
    print(f"micro_outline = {json.dumps(micro)}")