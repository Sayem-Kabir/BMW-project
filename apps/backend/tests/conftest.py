"""Override get_async_session for unit tests that should not require Postgres."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.main import app


@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=0)
    session.execute = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    return session


@pytest.fixture(autouse=True)
async def override_db(mock_db_session):
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db_session

    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()
