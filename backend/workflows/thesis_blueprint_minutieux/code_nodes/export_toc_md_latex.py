# Code Node: Export TOC (Layra Protocol)
def main(inputs):
    import json
    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try: return eval(v)
            except: return v
        return v

    micro = get_val("micro_outline", {})
    
    md = "# Thesis Blueprint\n\n"
    for ch in micro.get("chapters", []):
        md += f"## {ch.get('title')}\n"
        for sec in ch.get("sections", []):
            md += f"### {sec.get('title')}\n"
            for sub in sec.get("subsections", []):
                md += f"#### {sub.get('title')}\n- {sub.get('objective')}\n"
                
    exports = {"toc_md": md, "blueprint_json": json.dumps(micro)}
    
    print("####Global variable updated####")
    print(f"exports = {json.dumps(exports)}")