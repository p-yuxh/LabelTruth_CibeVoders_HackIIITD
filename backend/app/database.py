import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models.evidence_log import Base

logger = logging.getLogger("labeltruth.database")

# Primary and fallback engines
_engine = None
_sessionmaker = None


def get_engine():
    global _engine
    if _engine is None:
        try:
            # First attempt primary DATABASE_URL (PostgreSQL)
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                future=True,
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize PostgreSQL engine ({e}). "
                f"Falling back to SQLite: {settings.FALLBACK_DATABASE_URL}"
            )
            _engine = create_async_engine(
                settings.FALLBACK_DATABASE_URL,
                echo=False,
                future=True,
            )
    return _engine


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine()
        _sessionmaker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker


from sqlalchemy import text, inspect

def _sync_sqlite_schema(sync_conn):
    """Ensure newly added columns in Base metadata exist in existing SQLite tables."""
    try:
        inspector = inspect(sync_conn)
        for table_name, table in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(sync_conn.dialect)
                    sync_conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))
                    logger.info(f"Auto-migrated SQLite table '{table_name}': added column '{col.name}' ({col_type})")
    except Exception as e:
        logger.warning(f"SQLite schema sync warning: {e}")


async def init_db():
    """
    Test the database connection and create tables if they do not exist.
    If PostgreSQL is unreachable, dynamically switch to SQLite fallback.
    """
    global _engine, _sessionmaker
    engine = get_engine()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in str(engine.url):
                await conn.run_sync(_sync_sqlite_schema)
        logger.info(f"Database initialized successfully with URL: {engine.url}")
    except Exception as exc:
        logger.warning(
            f"Could not connect to primary database ({engine.url}): {exc}. "
            f"Switching to local fallback database ({settings.FALLBACK_DATABASE_URL})."
        )
        # Dispose primary engine and recreate with fallback
        await engine.dispose()
        _engine = create_async_engine(
            settings.FALLBACK_DATABASE_URL,
            echo=False,
            future=True,
        )
        _sessionmaker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_sync_sqlite_schema)
        logger.info(f"Fallback database initialized with: {_engine.url}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining database sessions with automatic resilience."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session


