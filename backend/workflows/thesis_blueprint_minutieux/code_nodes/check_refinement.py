# Code Node: Check Refinement (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    cov = get_val("coverage", {})
    iter_val = get_val("refine_iter", 0)
    max_iter = get_val("refine_iter_max", 2)
    
    gaps = cov.get("gaps", [])
    needs = (len(gaps) > 0) and (iter_val < max_iter)
    
    print("####Global variable updated####")
    print(f"needs_refinement = {needs}")
    print(f"refine_iter = {iter_val + 1}")