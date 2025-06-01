import re
from typing import Any, Dict


def unquote(s: str) -> str:
    if (s.startswith('"') and s.endswith('"')) or (
        s.startswith("'") and s.endswith("'")
    ):
        return s[1:-1]
    return s


def replace_template(s: str, obj: Dict[str, Any]) -> str:
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in obj:
            return match.group(0)  # 保留原模板
        value = obj[key]
        if isinstance(value, str):
            processed = unquote(value)
        else:
            processed = str(value)
        return processed

    # 替换所有模板变量
    replaced = re.sub(r"\{\{(\w+)\}\}", replacer, s)
    return replaced

def find_outermost_braces(s):
    start = -1
    brace_count = 0
    result = []
    
    for i, char in enumerate(s):
        if char == '{':
            brace_count += 1
            if brace_count == 1:
                start = i
        elif char == '}':
            if brace_count == 1 and start != -1:
                result.append(s[start:i+1])
            brace_count -= 1
            if brace_count == 0:
                start = -1
    return result