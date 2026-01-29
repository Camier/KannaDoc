"""
Repository Tests Package

This package contains tests for all repository classes and the factory pattern.
"""

from .fixtures import (
    # Database mocks
    mock_db,
    mock_collection,
    # Repository fixtures
    repository_factory,
    conversation_repo,
    knowledge_base_repo,
    file_repo,
    # Sample data
    sample_conversation,
    sample_knowledge_base,
    sample_file,
    sample_model_config,
    # FastAPI overrides
    override_get_db,
    override_get_factory,
    # Integration test fixtures
    real_db_connection,
    clean_test_db,
)

__all__ = [
    "mock_db",
    "mock_collection",
    "repository_factory",
    "conversation_repo",
    "knowledge_base_repo",
    "file_repo",
    "sample_conversation",
    "sample_knowledge_base",
    "sample_file",
    "sample_model_config",
    "override_get_db",
    "override_get_factory",
    "real_db_connection",
    "clean_test_db",
]
