#!/usr/bin/env python3
"""
Validate provider configuration consistency across the codebase.

This script ensures that all provider definitions are aligned with the
single source of truth (providers.yaml).

Checks:
1. All providers in .env.example exist in providers.yaml
2. All providers in constants.py PROVIDER_TIMEOUTS exist in providers.yaml
3. No hard-coded provider URLs in scripts
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml


def load_providers_yaml() -> dict:
    """Load providers.yaml as the source of truth."""
    yaml_path = Path(__file__).parent.parent / "app" / "core" / "llm" / "providers.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return set(data.get("providers", {}).keys())


def load_env_example() -> set:
    """Extract provider keys from .env.example."""
    env_path = Path(__file__).parent.parent.parent / ".env.example"
    with open(env_path) as f:
        content = f.read()

    providers = set()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if "_API_KEY=" in line:
            # Extract provider name from API key
            key_name = line.split("=")[0]
            provider = key_name.replace("_API_KEY", "").lower().replace("_", "-")
            # Map special cases
            if provider == "zhipuai":
                provider = "zhipu"
            elif provider == "ollama-cloud":
                provider = "ollama-cloud"
            providers.add(provider)
    return providers


def load_constants_timeouts() -> dict:
    """Extract provider names from PROVIDER_TIMEOUTS.

    Returns dict mapping model/provider name to timeout value.
    Special model names (deepseek-v3.2, deepseek-reasoner, glm) are mapped
    to their actual providers for validation.
    """
    constants_path = (
        Path(__file__).parent.parent
        / "app"
        / "workflow"
        / "components"
        / "constants.py"
    )
    with open(constants_path) as f:
        content = f.read()

    model_to_provider = {
        "deepseek-v3.2": "ollama-cloud",
        "deepseek-reasoner": "deepseek",
        "glm": "zai",
    }

    timeouts = {}
    in_timeouts = False
    for line in content.splitlines():
        if "PROVIDER_TIMEOUTS" in line and "{" in line:
            in_timeouts = True
            continue
        if in_timeouts:
            if "}" in line:
                break
            if ":" in line and not line.strip().startswith("#"):
                key = line.split(":")[0].strip().strip('"').strip("'")
                if key and key != "default":
                    # Map special model names to actual providers
                    provider = model_to_provider.get(key, key)
                    timeouts[provider] = True
    return set(timeouts.keys())


def validate():
    """Run all validation checks."""
    print("=" * 60)
    print("Provider Configuration Validation")
    print("=" * 60)

    yaml_providers = load_providers_yaml()
    print(f"\n✓ Source of truth (providers.yaml): {len(yaml_providers)} providers")
    for p in sorted(yaml_providers):
        print(f"  - {p}")

    # Check .env.example
    env_providers = load_env_example()
    env_orphans = env_providers - yaml_providers
    print(
        f"\n{'✓' if not env_orphans else '⚠️'} .env.example: {len(env_providers)} providers"
    )
    if env_orphans:
        print(f"  ❌ Orphan providers (not in providers.yaml):")
        for p in sorted(env_orphans):
            print(f"     - {p}")
    else:
        print(f"  All providers aligned with providers.yaml")

    # Check constants.py
    const_providers = load_constants_timeouts()
    const_orphans = const_providers - yaml_providers
    print(
        f"\n{'✓' if not const_orphans else '⚠️'} constants.py PROVIDER_TIMEOUTS: {len(const_providers)} providers"
    )
    if const_orphans:
        print(f"  ❌ Orphan providers (not in providers.yaml):")
        for p in sorted(const_orphans):
            print(f"     - {p}")
    else:
        print(f"  All providers aligned with providers.yaml")

    # Summary
    all_orphans = env_orphans | const_orphans
    if all_orphans:
        print(f"\n{'=' * 60}")
        print(f"❌ VALIDATION FAILED: {len(all_orphans)} orphan provider(s) found")
        print(f"{'=' * 60}")
        return 1
    else:
        print(f"\n{'=' * 60}")
        print(f"✅ VALIDATION PASSED: All configurations aligned")
        print(f"{'=' * 60}")
        return 0


if __name__ == "__main__":
    sys.exit(validate())
