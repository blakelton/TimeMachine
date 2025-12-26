"""Pytest fixtures and configuration for TimeMachine backend tests."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


# Note: event_loop fixture is no longer needed with pytest-asyncio >= 0.23
# when using asyncio_mode = "auto" in pyproject.toml


@pytest_asyncio.fixture
async def async_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage directory for testing."""
    storage_path = tmp_path / "storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


@pytest.fixture
def mock_sensor_reading() -> dict[str, Any]:
    """Create a mock sensor reading for testing."""
    return {
        "temperature": 22.5,
        "humidity": 45.0,
        "pressure": 1013.25,
        "error": None,
    }
