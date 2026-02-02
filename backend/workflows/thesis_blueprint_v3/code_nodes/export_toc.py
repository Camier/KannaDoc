# Code Node: Export TOC (Thesis Blueprint V3)
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

    macro = get_val("macro_outline", {})
    micro = get_val("micro_outline", {})

    if isinstance(macro, str):
        try:
            macro = json.loads(macro)
        except (ValueError, SyntaxError, TypeError):
            macro = {}
    if isinstance(micro, str):
        try:
            micro = json.loads(micro)
        except (ValueError, SyntaxError, TypeError):
            micro = {}

    # Generate MD and LaTeX export
    md = "# Thesis Table of Contents\n\n"
    latex = "\\tableofcontents\n\n"

    # Use micro chapters if available, otherwise fallback to macro
    chapters = micro.get("chapters", [])
    if not chapters and isinstance(macro, dict):
        chapters = macro.get("chapters", [])

    if isinstance(chapters, list):
        for i, ch in enumerate(chapters):
            if not isinstance(ch, dict):
                continue
            title = ch.get("title", f"Chapter {i + 1}")
            md += f"## {i + 1}. {title}\n"
            latex += f"\\section{{{title}}}\n"

            sections = ch.get("sections", [])
            if isinstance(sections, list):
                for j, sec in enumerate(sections):
                    if not isinstance(sec, dict):
                        continue
                    sec_title = sec.get("title", f"Section {j + 1}")
                    md += f"### {i + 1}.{j + 1} {sec_title}\n"
                    latex += f"\\subsection{{{sec_title}}}\n"

    exports = {"markdown": md, "latex": latex}

    print("####Global variable updated####")
    print(f"exports = {json.dumps(exports)}")
