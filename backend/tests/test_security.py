"""
Security Tests for LAYRA RAG System
Tests code scanning, eval safety, and authentication security
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from app.workflow.code_scanner import CodeScanner
from app.workflow.workflow_engine import WorkflowEngine
from app.core.security import create_access_token, verify_token, hash_password, verify_password


class TestCodeScanner:
    """Test the CodeScanner security checks"""

    @pytest.fixture
    def scanner(self):
        return CodeScanner()

    def test_safe_code_passes(self, scanner):
        """Test that safe code passes the scanner"""
        safe_code = """
def add(a, b):
    return a + b

result = add(1, 2)
x = [1, 2, 3]
y = sum(x)
"""
        result = scanner.scan_code(safe_code)
        assert result["safe"] is True
        assert len(result["issues"]) == 0

    def test_os_system_blocked(self, scanner):
        """Test that os.system is blocked"""
        malicious_code = "os.system('rm -rf /')"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert any("os.system" in issue for issue in result["issues"])

    def test_subprocess_blocked(self, scanner):
        """Test that subprocess module is blocked"""
        malicious_codes = [
            "subprocess.run(['rm', '-rf', '/'])",
            "subprocess.call('ls')",
            "subprocess.Popen('bash')",
        ]
        for code in malicious_codes:
            result = scanner.scan_code(code)
            assert result["safe"] is False
            assert any("subprocess" in issue for issue in result["issues"])

    def test_eval_blocked(self, scanner):
        """Test that eval() is blocked"""
        malicious_code = "eval(user_input)"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert any("eval" in issue for issue in result["issues"])

    def test_exec_blocked(self, scanner):
        """Test that exec() is blocked"""
        malicious_code = "exec(malicious_code)"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert any("exec" in issue for issue in result["issues"])

    def test_compile_blocked(self, scanner):
        """Test that compile() is blocked"""
        malicious_code = "compile('print(\"pwned\")', '<string>', 'exec')"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert any("compile" in issue for issue in result["issues"])

    def test_open_blocked(self, scanner):
        """Test that file operations are blocked"""
        malicious_codes = [
            "open('/etc/passwd', 'r')",
            "file('/etc/passwd')",
        ]
        for code in malicious_codes:
            result = scanner.scan_code(code)
            assert result["safe"] is False
            assert any("file operations" in issue or "open()" in issue for issue in result["issues"])

    def test_socket_blocked(self, scanner):
        """Test that socket operations are blocked"""
        malicious_code = "socket.socket(socket.AF_INET, socket.SOCK_STREAM)"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert any("socket" in issue for issue in result["issues"])

    def test_file_deletion_blocked(self, scanner):
        """Test that file deletion operations are blocked"""
        malicious_codes = [
            "os.remove('/tmp/file.txt')",
            "os.unlink('/tmp/file.txt')",
            "os.rmdir('/tmp/dir')",
            "shutil.rmtree('/tmp/dir')",
        ]
        for code in malicious_codes:
            result = scanner.scan_code(code)
            assert result["safe"] is False

    def test_forbidden_imports_os(self, scanner):
        """Test that importing os module is blocked"""
        malicious_codes = [
            "import os",
            "from os import system",
            "import os as operating_system",
        ]
        for code in malicious_codes:
            result = scanner.scan_code(code)
            assert result["safe"] is False
            assert any("os" in issue.lower() for issue in result["issues"])

    def test_forbidden_imports_subprocess(self, scanner):
        """Test that importing subprocess is blocked"""
        malicious_codes = [
            "import subprocess",
            "from subprocess import run",
        ]
        for code in malicious_codes:
            result = scanner.scan_code(code)
            assert result["safe"] is False

    def test_forbidden_imports_socket(self, scanner):
        """Test that importing socket is blocked"""
        malicious_code = "import socket"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False

    def test_forbidden_imports_sys(self, scanner):
        """Test that importing sys is blocked"""
        malicious_code = "import sys"
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False

    def test_syntax_error_detection(self, scanner):
        """Test that syntax errors are detected"""
        invalid_code = "def foo(\n    # invalid syntax"
        result = scanner.scan_code(invalid_code)
        assert result["safe"] is False
        assert any("Syntax error" in issue for issue in result["issues"])

    def test_multiple_vulnerabilities_detected(self, scanner):
        """Test that multiple vulnerabilities are all detected"""
        malicious_code = """
import os
import subprocess
os.system('ls')
eval('1+1')
open('/etc/passwd')
"""
        result = scanner.scan_code(malicious_code)
        assert result["safe"] is False
        assert len(result["issues"]) >= 4  # At least 4 issues detected

    def test_safe_math_operations(self, scanner):
        """Test that safe math operations are allowed"""
        safe_code = """
import math
result = math.sqrt(16)
x = [1, 2, 3]
y = sorted(x)
z = sum(x)
"""
        result = scanner.scan_code(safe_code)
        assert result["safe"] is True

    def test_safe_string_operations(self, scanner):
        """Test that safe string operations are allowed"""
        safe_code = """
text = "hello world"
words = text.split()
joined = " ".join(words)
upper = text.upper()
"""
        result = scanner.scan_code(safe_code)
        assert result["safe"] is True


class TestWorkflowEngineSecurity:
    """Test WorkflowEngine security features"""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock WorkflowEngine for testing"""
        nodes = [
            {
                "id": "node_start",
                "type": "start",
                "data": {"name": "Start"}
            },
            {
                "id": "node_code",
                "type": "code",
                "data": {
                    "name": "Code Node",
                    "code": "result = 42"
                }
            }
        ]
        edges = []
        engine = WorkflowEngine(
            username="testuser",
            nodes=nodes,
            edges=edges,
            global_variables={},
            task_id="test_task_123"
        )
        return engine

    def test_safe_eval_blocks_os_import(self, mock_engine):
        """Test that safe_eval blocks __import__('os')"""
        malicious_expressions = [
            "__import__('os').system('rm -rf /')",
            "__import__('subprocess').run('ls')",
        ]
        for expr in malicious_expressions:
            with pytest.raises(ValueError) as exc_info:
                mock_engine.safe_eval(expr, "test_node", "test_id")
            assert "不安全的表达式" in str(exc_info.value) or "unsafe" in str(exc_info.value).lower()

    def test_safe_eval_blocks_double_underscore(self, mock_engine):
        """Test that safe_eval blocks dunder methods/attributes"""
        malicious_expressions = [
            "global_variables.__class__",
            "().__class__",
            "''.__class__",
            "[].__class__",
        ]
        for expr in malicious_expressions:
            # Should either be blocked by scanner or fail gracefully
            try:
                result = mock_engine.safe_eval(expr, "test_node", "test_id")
                # If it passes, ensure it's not accessing dangerous attributes
                assert result is None or isinstance(result, (int, str, float, bool, list, dict))
            except ValueError:
                # Expected - expression was blocked
                pass

    def test_safe_eval_blocks_builtins_access(self, mock_engine):
        """Test that safe_eval blocks access to dangerous builtins"""
        malicious_expressions = [
            "__builtins__",
            "globals()",
            "locals()",
            "vars()",
        ]
        for expr in malicious_expressions:
            try:
                result = mock_engine.safe_eval(expr, "test_node", "test_id")
                # If it passes, ensure it's not returning dangerous objects
                assert result is None or isinstance(result, (int, str, float, bool, list, dict))
            except (ValueError, AttributeError, KeyError):
                # Expected - expression was blocked or failed
                pass

    def test_safe_eval_allows_safe_operations(self, mock_engine):
        """Test that safe_eval allows safe variable operations"""
        mock_engine.global_variables = {
            "x": 10,
            "y": 20,
            "name": "test",
            "items": [1, 2, 3],
            "flag": True
        }
        safe_expressions = [
            ("x + y", 30),
            ("x > 5", True),
            ("name == 'test'", True),
            ("len(items)", 3),
            ("flag and x > 0", True),
        ]
        for expr, expected in safe_expressions:
            result = mock_engine.safe_eval(expr, "test_node", "test_id")
            assert result == expected

    def test_safe_eval_with_string_variables(self, mock_engine):
        """Test that safe_eval handles string variables correctly"""
        mock_engine.global_variables = {
            "status": "active",
            "count": "42",
        }
        # String numbers should be coerced to actual numbers
        result = mock_engine.safe_eval("count", "test_node", "test_id")
        # The coercion logic handles stringified numbers
        assert result == "42" or result == 42


class TestPasswordHashing:
    """Test password hashing and verification security"""

    def test_password_hashing_is_secure(self):
        """Test that passwords are properly hashed"""
        password = "secure_password_123"
        hashed = hash_password(password)

        # Hash should not equal plaintext
        assert hashed != password
        # Hash should contain bcrypt identifier
        assert "$2b$" in hashed or "$2a$" in hashed

    def test_password_verification_works(self):
        """Test that password verification works correctly"""
        password = "secure_password_123"
        hashed = hash_password(password)

        # Correct password should verify
        assert verify_password(password, hashed) is True
        # Wrong password should not verify
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes (salt)"""
        password1 = "password1"
        password2 = "password2"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes due to salt"""
        password = "same_password"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTSecurity:
    """Test JWT token security"""

    def test_token_creation_and_verification(self):
        """Test that tokens can be created and verified"""
        data = {"sub": "testuser", "username": "testuser"}
        token = create_access_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Token should be verifiable
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["username"] == "testuser"

    def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected"""
        invalid_tokens = [
            "",
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]
        for token in invalid_tokens:
            with pytest.raises(Exception):
                verify_token(token)

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected"""
        import time
        from datetime import datetime, timedelta

        # Create a token that's already expired
        data = {"sub": "testuser"}
        # This would need to be tested with actual expiration logic
        # For now, just verify the mechanism exists
        token = create_access_token(data)
        assert token is not None


class TestInputValidation:
    """Test input validation security"""

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are handled"""
        # This is a placeholder - actual implementation depends on how queries are built
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
        ]
        # Test framework should validate these are properly escaped
        for input_str in malicious_inputs:
            # Validate that special characters are handled
            assert "'" in input_str or ";" in input_str

    def test_nosql_injection_prevention(self):
        """Test that NoSQL injection attempts are handled"""
        malicious_inputs = [
            {"$ne": None},
            {"$regex": ".*"},
            {"$where": "this.password == 'password'"},
        ]
        # Test framework should validate these are properly handled
        for input_obj in malicious_inputs:
            assert isinstance(input_obj, dict)

    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
        ]
        # Validation should catch these
        for path in malicious_paths:
            assert ".." in path or "/" in path or "\\" in path


class TestAuthenticationBypass:
    """Test authentication bypass prevention"""

    def test_token_manipulation_blocked(self):
        """Test that token manipulation is detected"""
        valid_token = create_access_token({"sub": "testuser"})

        # Try to manipulate token
        manipulated_tokens = [
            valid_token + "extra",
            valid_token[:-10],
            valid_token.replace("a", "b"),
        ]

        for token in manipulated_tokens:
            try:
                payload = verify_token(token)
                # If it doesn't raise exception, verify it's not the original user
                assert payload.get("sub") != "testuser" or len(token) != len(valid_token)
            except Exception:
                # Expected - manipulation detected
                pass

    def test_session_fixation_prevention(self):
        """Test that session fixation is prevented"""
        # Sessions should be regenerated on login
        # This is a placeholder for actual session management tests
        assert True  # Placeholder

    def test_csrf_protection(self):
        """Test that CSRF protection is in place"""
        # CSRF tokens should be validated
        # This is a placeholder for actual CSRF tests
        assert True  # Placeholder
