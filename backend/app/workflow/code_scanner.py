# workflow/code_scanner.py
import ast
import re
from typing import Dict, List, Optional, Tuple


class CodeScanner:
    FORBIDDEN_PATTERNS = [
        (r"os\.system\s*\(", "os.system() - shell command execution"),
        (
            r"subprocess\.(system|popen|call|run|check_call|check_output|Popen)\s*\(",
            "subprocess module - shell command execution",
        ),
        (r"eval\s*\(", "eval() - arbitrary code execution"),
        (r"exec\s*\(", "exec() - arbitrary code execution"),
        (r"compile\s*\(", "compile() - dynamic code generation"),
        (r"__import__\s*\(", "__import__() - dynamic module import"),
        (r"open\s*\(", "open() - file operations"),
        (r"file\s*\(", "file() - file operations"),
        (r"socket\s*\.", "socket module - network operations"),
        (r"os\.chmod\s*\(", "os.chmod() - file permission changes"),
        (r"os\.chown\s*\(", "os.chown() - file ownership changes"),
        (r"os\.remove\s*\(", "os.remove() - file deletion"),
        (r"os\.unlink\s*\(", "os.unlink() - file deletion"),
        (r"os\.rmdir\s*\(", "os.rmdir() - directory deletion"),
        (r"shutil\.rmtree\s*\(", "shutil.rmtree() - recursive directory deletion"),
        (r"shutil\.move\s*\(", "shutil.move() - file/directory move"),
        (r"mkdir\s*\(", "mkdir() - directory creation"),
        (r"os\.mkdir\s*\(", "os.mkdir() - directory creation"),
        (r"os\.rename\s*\(", "os.rename() - file/directory rename"),
    ]

    FORBIDDEN_IMPORTS = ["os", "subprocess", "socket", "sys", "builtins", "importlib"]

    def __init__(self):
        self.forbidden_keywords = [
            "os.system",
            "subprocess",
            "eval",
            "exec",
            "open",
            "__import__",
            "socket",
        ]

    def scan_code(self, code: str) -> Dict:
        issues: List[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"safe": False, "issues": [f"Syntax error: {str(e)}"]}

        issues.extend(self._check_patterns(code))
        issues.extend(self._check_ast_issues(tree))

        if issues:
            return {"safe": False, "issues": issues}

        return {"safe": True, "issues": []}

    def _check_patterns(self, code: str) -> List[str]:
        issues: List[str] = []
        for pattern, description in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                issues.append(f"Forbidden pattern: {description}")
        return issues

    def _check_ast_issues(self, tree: ast.AST) -> List[str]:
        issues: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ast.unparse(node.func)
                if any(kw == func_name for kw in self.forbidden_keywords):
                    issues.append(f"Forbidden function call: {func_name}")

            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in self.FORBIDDEN_IMPORTS:
                        issues.append(f"Forbidden import: {alias.name}")

            if isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in self.FORBIDDEN_IMPORTS:
                        issues.append(f"Forbidden import from: {node.module}")

        return issues
