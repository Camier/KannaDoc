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