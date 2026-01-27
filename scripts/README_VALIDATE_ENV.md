# Environment Validation Script

## Overview

`validate_env.py` validates your `.env` file against `.env.example` to ensure all required configuration variables are present and properly configured.

## Features

- **Missing Variable Detection**: Identifies required variables that are not set
- **Placeholder Detection**: Finds variables that still contain placeholder values like `your_secret_here`
- **Categorized Output**: Groups variables by type (Database, Security, API Keys, Services, Other)
- **CI/CD Ready**: Returns proper exit codes (0 = valid, 1 = invalid)
- **Strict Mode**: Optionally flag extra variables not in `.env.example`
- **Flexible Paths**: Works with any `.env` file location

## Usage

### Basic Usage

Validate the default `.env` file:

```bash
python3 scripts/validate_env.py
```

### Custom Environment File

Validate a specific environment file:

```bash
python3 scripts/validate_env.py --env-file .env.production
```

### Strict Mode

Treat extra variables (not in `.env.example`) as errors:

```bash
python3 scripts/validate_env.py --strict
```

### Verbose Output

Show additional information:

```bash
python3 scripts/validate_env.py --verbose
```

### CI/CD Integration

```bash
# In your CI pipeline
python3 scripts/validate_env.py || exit 1
```

## Exit Codes

- `0` - Validation passed (all required variables present, no placeholders)
- `1` - Validation failed (missing variables or placeholders detected)

## Output Examples

### Success Case

```
✅ ENVIRONMENT VALIDATION PASSED
============================================================
All required variables are present and properly configured.
```

### Missing Variables

```
❌ MISSING REQUIRED VARIABLES
============================================================

SECURITY:
  - SECRET_KEY
  - REDIS_PASSWORD

DATABASE:
  - MONGODB_URL
  - MINIO_ACCESS_KEY

Total missing: 4 variable(s)
```

### Placeholder Values

```
⚠️  PLACEHOLDER VALUES DETECTED
============================================================

The following variables still contain placeholder values:
  - OPENAI_API_KEY=sk-your-openai-api-key-here
  - SECRET_KEY=change_me
  - REDIS_PASSWORD=your_secure_redis_password_here

Total placeholders: 3 variable(s)
```

## Required vs Optional Variables

- **Required**: Variables in `.env.example` that are NOT commented out
- **Optional**: Variables in `.env.example` that start with `#` (commented)

Example:

```bash
# Required (not commented)
OPENAI_API_KEY=sk-...

# Optional (commented)
# DEEPSEEK_API_KEY=sk-...
```

## Placeholder Patterns

The script detects these placeholder patterns:

- `your_*_here` (e.g., `your_secret_here`)
- `your-*-here` (e.g., `your-api-key-here`)
- `change_me`
- `change-this`
- `placeholder`
- `xxx`
- `REPLACE_WITH`
- `sk-*-*-here` (e.g., `sk-your-key-here`)

## Integration with Docker Compose

Add to your deployment script:

```bash
#!/bin/bash
set -e

echo "Validating environment..."
python3 scripts/validate_env.py

echo "Starting services..."
docker-compose up -d
```

## Troubleshooting

### False Positives

If a legitimate value is flagged as a placeholder, ensure it doesn't match any placeholder patterns. For example:

- Bad: `OPENAI_API_KEY=sk-abc-here` (matches pattern)
- Good: `OPENAI_API_KEY=sk-abc123xyz` (doesn't match)

### Missing Variables

If variables are reported as missing but they exist in your `.env`:

1. Check for typos in variable names
2. Ensure the variable isn't commented out (no `#` at the start)
3. Verify the format: `VARIABLE_NAME=value` (no spaces around `=`)

### Adding New Variables

1. Add to `.env.example` (uncomment if already present)
2. Add to your `.env` file
3. Run validation script to verify

## Development

### Testing

```bash
# Test with missing variables
python3 scripts/validate_env.py --env-file /tmp/test_missing.env

# Test with placeholders
python3 scripts/validate_env.py --env-file /tmp/test_placeholders.env

# Test valid env
python3 scripts/validate_env.py --env-file /tmp/test_valid.env
```

### Code Quality

The script follows PEP 8 style guidelines and includes:
- Type hints
- Docstrings
- Error handling
- Clear separation of concerns

## See Also

- [Environment Configuration Best Practices](../docs/CONFIGURATION.md)
- [Docker Compose Configuration](../docker-compose.yml)
- [Deployment Guide](../README.md#deployment)
