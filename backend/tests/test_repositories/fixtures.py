"""
Test Fixtures for Repository Tests

Provides reusable pytest fixtures for testing repositories with:
- In-memory MongoDB mocking
- Repository factory injection
- Sample data generation

NOTE: Some fixtures that depend on factory.py are commented out as that module
does not currently exist in the codebase.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

# NOTE: factory.py does not exist - commented out
# from app.db.repositories.factory import RepositoryFactory
from app.db.repositories import (
    ConversationRepository,
    KnowledgeBaseRepository,
    FileRepository,
)


# ==============================================================================
# Database Mock Fixtures
# ==============================================================================

@pytest.fixture
def mock_db() -> AsyncMock:
    """
    Create a mock MongoDB database for testing.

    This fixture provides a mock database that can be used to test
    repository methods without connecting to a real database.

    Returns:
        AsyncMock: Mock AsyncIOMotorDatabase instance

    Example:
        def test_get_conversation(mock_db):
            mock_db.conversations.find_one.return_value = sample_conversation
            repo = ConversationRepository(db=mock_db)
            result = await repo.get_conversation("conv_123")
            assert result["conversation_id"] == "conv_123"
    """
    db = AsyncMock(spec=AsyncIOMotorDatabase)

    # Mock common collections
    db.conversations = AsyncMock()
    db.knowledge_bases = AsyncMock()
    db.files = AsyncMock()
    db.model_config = AsyncMock()
    db.chatflows = AsyncMock()
    db.workflows = AsyncMock()
    db.nodes = AsyncMock()

    return db


@pytest.fixture
def mock_collection():
    """
    Create a mock MongoDB collection.

    Returns:
        AsyncMock: Mock collection instance

    Example:
        def test_bulk_operations(mock_collection):
            mock_collection.insert_many.return_value = InsertManyResult([...], True)
            # Test bulk operations
    """
    collection = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find = MagicMock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.bulk_write = AsyncMock()

    return collection


# ==============================================================================
# Repository Factory Fixtures
# ==============================================================================

# NOTE: Commented out - depends on factory.py which doesn't exist
# @pytest.fixture
# def repository_factory(mock_db: AsyncMock) -> RepositoryFactory:
#     """
#     Create a RepositoryFactory with a mocked database.
#
#     This is the primary fixture for testing repositories in isolation.
#
#     Args:
#         mock_db: Mock database from fixture
#
#     Returns:
#         RepositoryFactory: Factory instance with mocked DB
#
#     Example:
#         def test_conversation_repository(repository_factory):
#             repo = repository_factory.conversation()
#             result = await repo.get_conversation("conv_123")
#             assert result is not None
#     """
#     return RepositoryFactory(db=mock_db)


@pytest.fixture
def conversation_repo(mock_db: AsyncMock) -> ConversationRepository:
    """
    Create a ConversationRepository with mocked database.

    Convenience fixture for tests that only need conversation repository.

    Args:
        mock_db: Mock database from fixture

    Returns:
        ConversationRepository: Repository instance

    Example:
        def test_create_conversation(conversation_repo):
            result = await repo.create_conversation(
                conversation_id="conv_123",
                username="test_user",
                conversation_name="Test Chat",
                model_config={},
            )
            assert result["status"] == "success"
    """
    return ConversationRepository(db=mock_db)


@pytest.fixture
def knowledge_base_repo(mock_db: AsyncMock) -> KnowledgeBaseRepository:
    """Create a KnowledgeBaseRepository with mocked database."""
    return KnowledgeBaseRepository(db=mock_db)


@pytest.fixture
def file_repo(mock_db: AsyncMock) -> FileRepository:
    """Create a FileRepository with mocked database."""
    return FileRepository(db=mock_db)


# ==============================================================================
# Sample Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_conversation() -> Dict[str, Any]:
    """
    Create sample conversation data for testing.

    Returns:
        Dictionary representing a conversation document

    Example:
        def test_conversation_serialization(sample_conversation):
            assert "conversation_id" in sample_conversation
            assert sample_conversation["username"] == "test_user"
    """
    return {
        "conversation_id": "test_conv_123",
        "conversation_name": "Test Conversation",
        "username": "test_user",
        "model_config": {
            "selected_model": "gpt-4",
            "temperature": 0.7,
        },
        "turns": [
            {
                "message_id": "msg_1",
                "parent_message_id": "",
                "user_message": "Hello",
                "ai_message": "Hi there!",
                "temp_db": "",
                "file_used": [],
                "status": "completed",
                "timestamp": "2024-01-01T12:00:00",
                "total_token": 100,
                "completion_tokens": 50,
                "prompt_tokens": 50,
            }
        ],
        "created_at": "2024-01-01T12:00:00",
        "last_modify_at": "2024-01-01T12:00:00",
        "is_read": False,
        "is_delete": False,
    }


@pytest.fixture
def sample_knowledge_base() -> Dict[str, Any]:
    """Create sample knowledge base data for testing."""
    return {
        "knowledge_base_id": "test_kb_123",
        "knowledge_base_name": "Test Knowledge Base",
        "username": "test_user",
        "files": [
            {
                "file_id": "file_1",
                "filename": "test.pdf",
                "minio_filename": "minio_test.pdf",
                "minio_url": "http://minio:9000/bucket/test.pdf",
                "created_at": "2024-01-01T12:00:00",
            }
        ],
        "used_chat": [],
        "created_at": "2024-01-01T12:00:00",
        "last_modify_at": "2024-01-01T12:00:00",
        "is_delete": False,
    }


@pytest.fixture
def sample_file() -> Dict[str, Any]:
    """Create sample file data for testing."""
    return {
        "file_id": "test_file_123",
        "filename": "test_document.pdf",
        "username": "test_user",
        "minio_filename": "minio_test_file.pdf",
        "minio_url": "http://minio:9000/bucket/test.pdf",
        "knowledge_db_id": "test_kb_123",
        "images": [
            {
                "images_id": "img_1",
                "minio_filename": "page_1.png",
                "minio_url": "http://minio:9000/bucket/page_1.png",
                "page_number": "1",
            }
        ],
        "created_at": "2024-01-01T12:00:00",
        "last_modify_at": "2024-01-01T12:00:00",
        "is_delete": False,
    }


@pytest.fixture
def sample_model_config() -> Dict[str, Any]:
    """Create sample model configuration for testing."""
    return {
        "username": "test_user",
        "selected_model": "model_1",
        "models": [
            {
                "model_id": "model_1",
                "model_name": "GPT-4",
                "model_url": "https://api.openai.com/v1",
                "api_key": "sk-test",
                "base_used": ["knowledge_base_1"],
                "system_prompt": "You are a helpful assistant.",
                "temperature": 0.7,
                "max_length": 2000,
                "top_P": 0.9,
                "top_K": 50,
                "score_threshold": 0.5,
            }
        ],
    }


# ==============================================================================
# FastAPI Test Client Fixtures
# ==============================================================================

@pytest.fixture
def override_get_db(mock_db: AsyncMock):
    """
    Override the get_database dependency for testing FastAPI endpoints.

    This fixture allows you to test endpoints without connecting to a real database.

    Args:
        mock_db: Mock database from fixture

    Yields:
        None (applies override, then cleans up)

    Example:
        def test_get_conversation_endpoint(override_get_db, client):
            response = await client.get("/api/v1/conversations/conv_123")
            assert response.status_code == 200
    """
    # NOTE: Updated to not import from factory.py which doesn't exist
    # This fixture would need to be adapted to your actual dependency injection setup

    # Override the dependency
    async def override_get_database():
        return mock_db

    # Apply override (implementation depends on your DI framework)
    # original = get_database
    # get_database = override_get_database

    yield mock_db  # Just yield the mock_db for direct use

    # Restore original
    # get_database = original


# NOTE: Commented out - depends on factory.py which doesn't exist
# @pytest.fixture
# def override_get_factory(repository_factory: RepositoryFactory):
#     """
#     Override the get_factory dependency for testing FastAPI endpoints.
#
#     Similar to override_get_db but provides the full factory.
#
#     Args:
#         repository_factory: Factory with mocked DB
#
#     Yields:
#         None (applies override, then cleans up)
#
#     Example:
#         def test_create_conversation_endpoint(override_get_factory, client):
#             response = await client.post(
#                 "/api/v1/conversations",
#                 json={...}
#             )
#             assert response.status_code == 201
#     """
#     from app.db.repositories.factory import get_factory
#
#     async def override_get_factory():
#         return repository_factory
#
#     original = get_factory
#     get_factory = override_get_factory
#
#     yield
#
#     get_factory = original


# ==============================================================================
# Integration Test Fixtures (Optional - for real DB testing)
# ==============================================================================

@pytest.fixture(scope="session")
def real_db_connection():
    """
    Create a real MongoDB connection for integration tests.

    This fixture is optional and only used when you want to test
    against a real database (e.g., in CI/CD).

    NOTE: This requires MONGO_TEST_URL environment variable.

    Yields:
        AsyncIOMotorClient: Real database connection

    Example:
        @pytest.mark.integration
        async def test_real_db_insert(real_db_connection):
            result = await real_db_connection.test_collection.insert_one({"test": "data"})
            assert result.inserted_id is not None
    """
    import os
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.getenv("MONGO_TEST_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)

    yield client

    # Cleanup
    client.close()


@pytest.fixture
def clean_test_db(real_db_connection):
    """
    Provide a clean database for integration testing.

    This fixture creates a temporary database and cleans it up after the test.

    Yields:
        AsyncIOMotorDatabase: Clean test database

    Example:
        @pytest.mark.integration
        async def test_with_clean_db(clean_test_db):
            # Use clean_test_db for testing
            await clean_test_db.conversations.insert_one({...})
            # Database is automatically cleaned up after test
    """
    import uuid

    test_db_name = f"test_db_{uuid.uuid4().hex[:8]}"
    db = real_db_connection[test_db_name]

    yield db

    # Cleanup: Drop the entire test database
    real_db_connection.drop_database(test_db_name)
