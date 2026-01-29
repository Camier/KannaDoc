# Code Node: Coverage Scoring (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    micro = get_val("micro_outline", {})
    reqs = get_val("requirements", {})
    min_src = reqs.get("quality_gates", {}).get("min_sources_per_subsection", 3)
    
    gaps = []
    for ch in micro.get("chapters", []):
        for sec in ch.get("sections", []):
            for sub in sec.get("subsections", []):
                if len(sub.get("candidate_sources", [])) < min_src:
                    gaps.append(sub.get("subsection_id"))
                    
    coverage = {"gaps": gaps, "total_gaps": len(gaps)}
    
    print("####Global variable updated####")
    print(f"coverage = {json.dumps(coverage)}")
    print(f"gaps_found = {len(gaps) > 0}")