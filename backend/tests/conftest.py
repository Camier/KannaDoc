# tests/conftest.py
import pytest
import pytest_asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, Mock


# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create mock modules to prevent actual imports
sys.modules['app.utils.kafka_producer'] = Mock()
sys.modules['app.utils.kafka_consumer'] = Mock()
sys.modules['app.utils.kafka_producer'].kafka_producer_manager = MagicMock()
sys.modules['app.utils.kafka_producer'].kafka_producer_manager.start = AsyncMock()
sys.modules['app.utils.kafka_consumer'].kafka_consumer_manager = MagicMock()
sys.modules['app.utils.kafka_consumer'].kafka_consumer_manager.consume_messages = AsyncMock()
sys.modules['app.utils.kafka_consumer'].kafka_consumer_manager.stop = AsyncMock()
sys.modules['docker'] = Mock()  # Mock docker module


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a test database engine"""
    # Import here to avoid early initialization
    from app.db.mysql_base import Base

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(engine) -> AsyncSession:
    """Create a test database session"""
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession):
    """
    Create an AsyncClient for testing FastAPI endpoints.
    This fixture sets up dependency overrides to use the test database.
    """
    # Mock Redis
    mock_redis_instance = MagicMock()
    mock_redis_instance.get_token_connection = AsyncMock()
    mock_redis_instance.get_task_connection = AsyncMock()

    # Mock Mongo
    mock_mongo_instance = MagicMock()
    mock_mongo_instance.connect = AsyncMock()

    # Mock MinIO
    mock_minio_instance = MagicMock()
    mock_minio_instance.init_minio = AsyncMock()

    # Patch Redis and Mongo modules
    import app.db.redis as redis_module
    import app.db.mongo as mongo_module
    import app.db.miniodb as minio_module

    original_redis = redis_module.redis
    original_mongo = mongo_module.mongodb
    original_minio = minio_module.async_minio_manager

    redis_module.redis = mock_redis_instance
    mongo_module.mongodb = mock_mongo_instance
    minio_module.async_minio_manager = mock_minio_instance

    try:
        # Import app after setting up mocks
        from app.main import app
        from app.db.mysql_session import get_mysql_session
        from app.db.mongo import get_mongo

        # Override database dependency to use test database
        async def override_get_mysql_session():
            yield db

        # Mock MongoDB dependency for the auth endpoint
        async def mock_get_mongo():
            mock_mongo_for_dep = AsyncMock()
            mock_mongo_for_dep.create_model_config = AsyncMock(return_value={"status": "success"})
            return mock_mongo_for_dep

        app.dependency_overrides[get_mysql_session] = override_get_mysql_session
        app.dependency_overrides[get_mongo] = mock_get_mongo

        # Create AsyncClient with ASGI transport
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

        # Clean up overrides
        app.dependency_overrides.clear()
    finally:
        # Restore original values
        redis_module.redis = original_redis
        mongo_module.mongodb = original_mongo
        minio_module.async_minio_manager = original_minio
