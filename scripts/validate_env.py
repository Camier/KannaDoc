#!/usr/bin/env python3
"""
Validate .env file against .env.example

Usage:
    python scripts/validate_env.py
    python scripts/validate_env.py --env-file /path/to/.env

Exit codes:
    0 (valid) - All required variables present and no placeholder values
    1 (invalid) - Missing required variables or placeholder values detected
"""
import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Placeholder patterns that indicate a value hasn't been set
# Note: These are conservative patterns to avoid false positives
PLACEHOLDER_PATTERNS = [
    r'^your_.*_here$',       # your_secret_key_here
    r'^your-.*-here$',       # your-api-key-here
    r'^change_me$',
    r'^change-this$',
    r'^placeholder$',
    r'^xxx$',
    r'^REPLACE_WITH',
    r'^sk-.*-here$',         # sk-your-key-here (not sk-abc123xyz)
]


def is_placeholder_value(value: str) -> bool:
    """Check if a value matches placeholder patterns"""
    if not value:
        return False

    value_lower = value.lower().strip()
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, value_lower, re.IGNORECASE):
            return True
    return False


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """
    Parse .env file and return dictionary of variables

    Format:
    - Lines starting with # are comments (ignored)
    - Lines with KEY=VALUE are parsed
    - Empty lines are ignored
    - Values can be wrapped in quotes (stripped during parsing)
    """
    if not file_path.exists():
        return {}

    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def get_required_vars_from_example(example_path: Path) -> Set[str]:
    """
    Parse .env.example and return set of required variable names

    Rules:
    - Variables not starting with # are required
    - Variables starting with # are optional (commented out)
    - Only lines containing = are considered
    """
    required_vars = set()
    optional_vars = set()

    if not example_path.exists():
        print(f"ERROR: .env.example not found at {example_path}")
        sys.exit(1)

    with open(example_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and section headers
            if not line or line.startswith('# ='):
                continue

            # Check if line is commented
            is_commented = line.startswith('#')

            # Extract variable name if present
            if '=' in line:
                # Remove leading comment character for parsing
                parse_line = line.lstrip('#').strip()

                if '=' in parse_line:
                    key = parse_line.split('=')[0].strip()

                    # Alphanumeric with underscores only
                    if key and re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                        if is_commented:
                            optional_vars.add(key)
                        else:
                            required_vars.add(key)

    return required_vars, optional_vars


def categorize_variables(required: Set[str], optional: Set[str]) -> Dict[str, List[str]]:
    """
    Categorize required variables by type for better error messages
    """
    categories = {
        'database': [],
        'security': [],
        'api_keys': [],
        'services': [],
        'other': []
    }

    # Keywords for categorization
    security_keywords = ['SECRET', 'PASSWORD', 'TOKEN', 'KEY', 'AUTH']
    api_key_keywords = ['API_KEY', 'OPENAI', 'DEEPSEEK', 'ANTHROPIC', 'GEMINI', 'ZHIPU', 'MOONSHOT', 'MINIMAX', 'COHERE', 'OLLAMA', 'JINA', 'HF_TOKEN']
    database_keywords = ['MONGO', 'MYSQL', 'REDIS', 'MILVUS', 'MINIO', 'NEO4J']
    service_keywords = ['KAFKA', 'UNOSERVER', 'SANDBOX', 'EMBEDDING', 'COLBERT', 'MODEL']

    for var in required:
        var_upper = var.upper()

        if any(kw in var_upper for kw in api_key_keywords):
            categories['api_keys'].append(var)
        elif any(kw in var_upper for kw in security_keywords):
            categories['security'].append(var)
        elif any(kw in var_upper for kw in database_keywords):
            categories['database'].append(var)
        elif any(kw in var_upper for kw in service_keywords):
            categories['services'].append(var)
        else:
            categories['other'].append(var)

    return categories


def validate_env(
    env_path: Path,
    example_path: Path,
    strict: bool = False
) -> Tuple[List[str], List[str], List[str]]:
    """
    Validate .env against .env.example

    Returns:
        Tuple of (missing_vars, placeholder_vars, extra_vars)
    """
    # Parse files
    env_vars = parse_env_file(env_path)
    required_vars, optional_vars = get_required_vars_from_example(example_path)

    # Check for missing required variables
    missing_vars = []
    for var in required_vars:
        if var not in env_vars:
            missing_vars.append(var)

    # Check for placeholder values in required variables
    placeholder_vars = []
    for var in required_vars:
        if var in env_vars and is_placeholder_value(env_vars[var]):
            placeholder_vars.append(f"{var}={env_vars[var]}")

    # Check for extra variables (only in strict mode)
    extra_vars = []
    if strict:
        for var in env_vars:
            if var not in required_vars and var not in optional_vars:
                extra_vars.append(var)

    return missing_vars, placeholder_vars, extra_vars


def print_validation_results(
    missing: List[str],
    placeholders: List[str],
    extra: List[str],
    verbose: bool = False
) -> None:
    """Print validation results with clear formatting"""

    has_errors = False

    # Print missing variables
    if missing:
        has_errors = True
        print("\n❌ MISSING REQUIRED VARIABLES")
        print("=" * 60)

        categories = categorize_variables(set(missing), set())

        for category, vars_list in categories.items():
            if vars_list:
                print(f"\n{category.upper()}:")
                for var in sorted(vars_list):
                    print(f"  - {var}")

        print(f"\nTotal missing: {len(missing)} variable(s)")

    # Print placeholder values
    if placeholders:
        has_errors = True
        print("\n⚠️  PLACEHOLDER VALUES DETECTED")
        print("=" * 60)
        print("\nThe following variables still contain placeholder values:")
        for item in sorted(placeholders):
            print(f"  - {item}")
        print(f"\nTotal placeholders: {len(placeholders)} variable(s)")

    # Print extra variables (strict mode)
    if extra:
        print("\nⓘ EXTRA VARIABLES (not in .env.example)")
        print("=" * 60)
        for var in sorted(extra):
            print(f"  - {var}")
        print(f"\nTotal extra: {len(extra)} variable(s)")

    # Print success message
    if not has_errors:
        print("\n✅ ENVIRONMENT VALIDATION PASSED")
        print("=" * 60)
        print("All required variables are present and properly configured.")
        if extra and verbose:
            print(f"\nNote: {len(extra)} extra variable(s) found in .env but not in .env.example")


def main():
    parser = argparse.ArgumentParser(
        description='Validate .env file against .env.example',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_env.py
  python scripts/validate_env.py --env-file .env.production
  python scripts/validate_env.py --strict
  python scripts/validate_env.py --verbose

Exit codes:
  0 - Validation passed
  1 - Validation failed (missing variables or placeholders)
        """
    )

    parser.add_argument(
        '--env-file',
        type=str,
        default='.env',
        help='Path to .env file (default: .env)'
    )

    parser.add_argument(
        '--example-file',
        type=str,
        default='.env.example',
        help='Path to .env.example file (default: .env.example)'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat extra variables as errors'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent
    env_path = project_root / args.env_file
    example_path = project_root / args.example_file

    # Check if .env exists
    if not env_path.exists():
        print(f"❌ ERROR: .env file not found at {env_path}")
        print(f"\nTo create it from the template:")
        print(f"  cp {args.example_file} {args.env_file}")
        print(f"\nThen edit {args.env_file} with your configuration.")
        sys.exit(1)

    # Run validation
    missing, placeholders, extra = validate_env(
        env_path,
        example_path,
        strict=args.strict
    )

    # Print results
    print_validation_results(missing, placeholders, extra, verbose=args.verbose)

    # Exit with appropriate code
    if missing or placeholders:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
