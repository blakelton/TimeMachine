"""Database session management with SQLite WAL mode optimization."""

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

logger = structlog.get_logger(__name__)


def set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Configure SQLite pragmas for optimal performance and SD card longevity.

    Args:
        dbapi_connection: The DBAPI connection.
        connection_record: The connection record.
    """
    cursor = dbapi_connection.cursor()

    # WAL mode - reduces write amplification, better for SD cards
    cursor.execute("PRAGMA journal_mode=WAL")

    # Normal sync - balance of safety and performance
    # FULL would be safer but wears SD card faster
    cursor.execute("PRAGMA synchronous=NORMAL")

    # Memory-mapped I/O - reduces syscalls
    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB

    # Increase cache size (negative means KB, positive means pages)
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")

    # Busy timeout - wait up to 5 seconds on locked database
    cursor.execute("PRAGMA busy_timeout=5000")

    cursor.close()


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with optimized settings.

    Returns:
        Configured async engine.
    """
    # Ensure parent directory exists
    if not settings.db_path.parent.exists():
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("created_db_directory", path=str(settings.db_path.parent))

    # Use StaticPool for SQLite (single connection per process)
    # NullPool would create/destroy connections frequently
    poolclass = StaticPool if settings.env == "development" else NullPool

    engine = create_async_engine(
        settings.database_url,
        poolclass=poolclass,
        echo=settings.debug,
        # Connection arguments for aiosqlite
        connect_args={
            "check_same_thread": False,  # Required for async
        },
    )

    # Register pragma configuration for synchronous engine
    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection: Any, connection_record: Any) -> None:
        set_sqlite_pragmas(dbapi_connection, connection_record)

    logger.info(
        "database_engine_created",
        url=settings.database_url,
        poolclass=poolclass.__name__,
    )

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session factory.

    Args:
        engine: The async engine.

    Returns:
        Session factory for creating database sessions.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Global engine and session factory
engine = create_engine()
SessionFactory = create_session_factory(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions.

    Yields:
        Database session.
    """
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in SQLAlchemy models.
    """
    from app.db.base import Base
    # Import all models to ensure they're registered with Base
    import app.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_created")


async def checkpoint_wal() -> None:
    """Checkpoint WAL file to prevent unbounded growth.

    Should be called periodically (e.g., hourly) via background task.
    """
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        logger.debug("wal_checkpoint_completed")
