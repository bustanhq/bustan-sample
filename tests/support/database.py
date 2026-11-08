"""Helpers for the tests that use the SQLite backend."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from bustan import ConfigService

from bustan_sample.platform.database import Database

BACKENDS = ["memory", "sqlite"]


def memory_database() -> Database:
    """Return a Database for the memory backend. Its transactions have no rollback."""
    return Database(ConfigService({}))


def sqlite_config(path: Path, **values: object) -> ConfigService:
    """Return a configuration for the SQLite backend on the file, with the given values."""
    return ConfigService(
        {"DATABASE_BACKEND": "sqlite", "DATABASE_SQLITE_PATH": str(path), **values}
    )


@asynccontextmanager
async def open_sqlite(path: Path) -> AsyncGenerator[Database]:
    """Open a Database on the file, as the startup of the application does."""
    database = Database(sqlite_config(path))
    await database.on_module_init()
    try:
        yield database
    finally:
        await database.on_module_destroy()
