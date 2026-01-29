# Code Node: Get Axis By Index (Layra Protocol)
def main(inputs):
    import json
    from ast import literal_eval as parse_val
    # Variables in Layra are often strings that need eval
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return parse_val(v)
            except: return v
        return v

    idx = get_val("loop_idx", 0)
    axes = get_val("seed_axes", [])
    
    print("####Global variable updated####")
    if idx < len(axes):
        axis = axes[idx]
        # Must expose 'axis' for prompt {{axis}}
        val = json.dumps(axis)
        print(f"axis = {val}")
    else:
        print("axis = ''")