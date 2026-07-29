from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Primary write engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_size=max(1, int(settings.db_pool_size)),
    max_overflow=max(0, int(settings.db_max_overflow)),
)

# Optional analytics read replica (Phase 13) — falls back to primary
_read_url = (settings.database_url_read or "").strip() or settings.database_url
read_engine = (
    create_async_engine(
        _read_url,
        echo=False,
        future=True,
        pool_size=max(1, int(settings.db_pool_size)),
        max_overflow=max(0, int(settings.db_max_overflow)),
    )
    if _read_url != settings.database_url
    else engine
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

read_session_maker = async_sessionmaker(
    read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

Base = declarative_base()


async def get_async_session():
    """Dependency for getting async session (primary)."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_read_session():
    """Analytics / leaderboard reads — replica when DATABASE_URL_READ set."""
    async with read_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
