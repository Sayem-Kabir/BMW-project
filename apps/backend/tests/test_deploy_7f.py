"""Unit tests for Render DATABASE_URL normalization (Module 7F)."""

from app.core.config import _normalize_database_urls


def test_normalize_render_postgres_url():
    async_url, sync_url = _normalize_database_urls(
        "postgres://user:pass@host/db",
        "",
    )
    assert async_url.startswith("postgresql+asyncpg://")
    assert sync_url.startswith("postgresql://")
    assert "user:pass@host/db" in async_url


def test_normalize_keeps_asyncpg():
    async_url, sync_url = _normalize_database_urls(
        "postgresql+asyncpg://bmwai:bmwai_secret@localhost:5432/bmwai_db",
        "postgresql://bmwai:bmwai_secret@localhost:5432/bmwai_db",
    )
    assert async_url.startswith("postgresql+asyncpg://")
    assert sync_url.startswith("postgresql://")
