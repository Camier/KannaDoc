# Code Node: Inc Subsection (Layra Protocol)
def main(inputs):
    from ast import literal_eval as parse_val

    def get_val(key, default):
        v = inputs.get(key, default)
        if isinstance(v, str) and v != "":
            try:
                return parse_val(v)
            except (ValueError, SyntaxError):
                return v
        return v

    idx = get_val("subsection_idx", 0)
    print("####Global variable updated####")
    print(f"subsection_idx = {idx + 1}")
