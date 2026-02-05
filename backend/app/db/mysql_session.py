from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from app.core.config import settings
from typing import AsyncGenerator, Optional


class MySQL:
    def __init__(self):
        self.engine: AsyncEngine = create_async_engine(
            settings.db_url,
            echo=settings.debug_mode,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
        self.async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            yield session

    async def close(self):
        await self.engine.dispose()


_mysql_instance: Optional[MySQL] = None


def get_mysql_instance() -> MySQL:
    global _mysql_instance
    if _mysql_instance is None:
        _mysql_instance = MySQL()
    return _mysql_instance


async def close_mysql() -> None:
    if _mysql_instance is not None:
        await _mysql_instance.close()


async def get_mysql_session() -> AsyncGenerator[AsyncSession, None]:
    mysql_instance = get_mysql_instance()
    async for session in mysql_instance.get_session():
        yield session
