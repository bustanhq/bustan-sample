import asyncio
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import aiosqlite
from bustan import ConfigService, Injectable

type Parameters = Iterable[object] | dict[str, object]


class DatabaseBackend(StrEnum):
    MEMORY = "memory"
    SQLITE = "sqlite"


@Injectable()
class Database:
    """The SQLite connection of the process, if DATABASE_BACKEND is sqlite.

    on_module_init opens the file in DATABASE_SQLITE_PATH, and on_module_destroy
    closes it. Thus the adapters can use the connection in each other hook.
    With the memory backend, the class opens nothing.

    The process has one connection. A lock gives each statement or transaction
    the connection for itself, thus statements of two requests never mix in
    one transaction. Between processes, SQLite locks the file. WAL mode lets
    readers continue while a process writes.
    """

    def __init__(self, config: ConfigService) -> None:
        self.backend = DatabaseBackend(str(config.get("DATABASE_BACKEND", "memory")))
        self._path = Path(
            str(config.get("DATABASE_SQLITE_PATH", "var/bustan-sample.db"))
        )
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    @property
    def is_sqlite(self) -> bool:
        return self.backend is DatabaseBackend.SQLITE

    async def on_module_init(self) -> None:
        if not self.is_sqlite:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level None: each statement commits, except in transaction().
        connection = await aiosqlite.connect(self._path, isolation_level=None)
        connection.row_factory = aiosqlite.Row
        for pragma in (
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA busy_timeout = 5000",
            "PRAGMA foreign_keys = ON",
        ):
            await connection.execute(pragma)
        self._lock = asyncio.Lock()
        self._connection = connection

    async def on_module_destroy(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    # Each method closes its cursor before it releases the lock. Thus no
    # statement keeps a read or a write open after the method returns.

    async def execute(self, sql: str, parameters: Parameters = ()) -> int:
        """Run one statement. Return the number of changed rows."""
        async with self._lock, self._open().execute(sql, parameters) as cursor:
            return cursor.rowcount

    async def execute_script(self, script: str) -> None:
        """Run statements that change the schema, for example CREATE TABLE IF NOT EXISTS."""
        async with self._lock, self._open().executescript(script):
            pass

    async def fetch_one(
        self, sql: str, parameters: Parameters = ()
    ) -> aiosqlite.Row | None:
        async with self._lock, self._open().execute(sql, parameters) as cursor:
            return await cursor.fetchone()

    async def fetch_all(
        self, sql: str, parameters: Parameters = ()
    ) -> list[aiosqlite.Row]:
        """Return all rows. Use it also for a statement with RETURNING."""
        async with self._lock, self._open().execute(sql, parameters) as cursor:
            return list(await cursor.fetchall())

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection]:
        """Give the connection for statements that must all commit, or none.

        BEGIN IMMEDIATE takes the write lock of the file at the start. If the
        block raises an error, the transaction rolls back.
        """
        async with self._lock:
            connection = self._open()
            await connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                await connection.execute("ROLLBACK")
                raise
            await connection.execute("COMMIT")

    def _open(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError(
                "the database is not open. Set DATABASE_BACKEND=sqlite, "
                "and start the application"
            )
        return self._connection


def to_text(moment: datetime) -> str:
    """Return the time as UTC text with a fixed length, thus text order is time order."""
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


def from_text(text: str) -> datetime:
    return datetime.fromisoformat(text)
