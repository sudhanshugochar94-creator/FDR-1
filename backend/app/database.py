from collections.abc import AsyncGenerator
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

database_backend = make_url(settings.DATABASE_URL).get_backend_name()
using_local_fallback = False


class Base(DeclarativeBase):
    pass


async def initialize_database() -> None:
    global engine, async_session_maker, database_backend, using_local_fallback

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (OperationalError, OSError, TimeoutError) as exc:
        if database_backend != "postgresql":
            raise

        error_text = str(getattr(exc, "orig", exc)).lower()
        if not any(
            reason in error_text
            for reason in ("refused", "could not connect", "timed out", "timeout")
        ):
            raise

        database_path = Path(settings.LOCAL_DATABASE_PATH)
        if not database_path.is_absolute():
            database_path = Path(__file__).resolve().parents[1] / database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)

        await engine.dispose()
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path.as_posix()}",
            echo=False,
            future=True,
        )
        async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        database_backend = "sqlite"
        using_local_fallback = True
        logger.warning(
            "PostgreSQL is unavailable; using persistent local SQLite database at %s",
            database_path,
        )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
