import pytest


@pytest.mark.unit
def test_provider_inventory_includes_core_thesis_providers() -> None:
    """Thesis deployment expects these providers to exist in the codebase.

    We do NOT enforce that only these providers exist (zai/minimax are supported too);
    this is a regression guard against accidental renames/removals.
    """

    from app.rag.provider_client import ProviderClient

    providers = set(ProviderClient.get_all_providers())
    assert "cliproxyapi" in providers
    assert "ollama-cloud" in providers
    assert "deepseek" in providers

