import re
from typing import Any, Dict


def safe_unicode_unescape(s):
    """安全处理含中文的转义字符串"""
    escape_map = {r"\n": "\n", r"\t": "\t", r"\r": "\r", r"\\": "\\"}
    for esc, char in escape_map.items():
        s = s.replace(esc, char)
    return s


def unquote(s: str) -> str:
    if (s.startswith('"') and s.endswith('"')) or (
        s.startswith("'") and s.endswith("'")
    ):
        return safe_unicode_unescape(s[1:-1])
    return safe_unicode_unescape(s)


def replace_template(s: str, obj: Dict[str, Any]) -> str:
    """
    将模板中的 {{ variable }} 替换为字典中对应的字符串值
    :param s: 包含 {{ 变量 }} 的模板字符串
    :param obj: 包含键值对的字典
    :return: 替换后的字符串
    """

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
    replaced = re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, s)
    return replaced


def find_outermost_braces(s):
    """Extract outermost JSON objects, handling braces inside strings."""
    result = []
    i = 0
    n = len(s)

    while i < n:
        if s[i] == "{":
            start = i
            brace_count = 1
            in_string = False
            i += 1

            while i < n and brace_count > 0:
                char = s[i]

                if char == "\\" and in_string and i + 1 < n:
                    i += 2
                    continue

                if char == '"':
                    in_string = not in_string
                elif not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1

                i += 1

            if brace_count == 0:
                result.append(s[start:i])
        else:
            i += 1

    return result
