import math
import time
from collections import OrderedDict, deque
from collections.abc import Callable

from bustan import ThrottleState

from bustan_sample.platform.database import Database, Migration

MAX_MEMORY_KEYS = 10_000

# Add a migration with the next version for each change. Never edit one.
_V1 = """
CREATE TABLE IF NOT EXISTS throttle_hits (
    key TEXT NOT NULL,
    at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS throttle_hits_by_key ON throttle_hits (key, at);
CREATE INDEX IF NOT EXISTS throttle_hits_by_time ON throttle_hits (at);
"""
MIGRATIONS = (Migration(1, "create the table throttle_hits", _V1),)


class BackendThrottlerStorage:
    """The bustan throttler storage for the memory and the SQLite backend.

    It counts the requests of each key in a sliding window of ttl seconds. A
    refused request is not counted, thus a caller that tries again does not
    make its own wait longer.

    bustan takes the storage in ThrottlerModule.for_root(), when Python imports
    the root module. The Database exists later. Thus the root module gives one
    instance of this class to the throttler, and ThrottlingModule binds that
    instance to the Database at each startup. Each startup also starts with
    empty memory windows.

    With the SQLite backend, all processes on the same file share the counts.
    A transaction with BEGIN IMMEDIATE makes the count and the report atomic.
    """

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._database: Database | None = None
        self._windows: OrderedDict[str, deque[float]] = OrderedDict()
        self._max_ttl = 0

    async def bind(self, database: Database) -> None:
        self._windows = OrderedDict()
        self._database = database if database.is_sqlite else None
        if self._database is not None:
            await self._database.migrate("throttling", MIGRATIONS)

    def unbind(self) -> None:
        self._database = None
        self._windows = OrderedDict()

    async def count_request(self, key: str, ttl: int, limit: int) -> ThrottleState:
        now = self._clock()
        self._max_ttl = max(self._max_ttl, ttl)
        if self._database is None:
            return self._count_in_memory(key, ttl, limit, now)
        return await self._count_in_sqlite(self._database, key, ttl, limit, now)

    def _count_in_memory(self, key: str, ttl: int, limit: int, now: float) -> ThrottleState:
        window = self._windows.pop(key, deque())
        while window and window[0] <= now - ttl:
            window.popleft()
        self._windows[key] = window
        while len(self._windows) > MAX_MEMORY_KEYS:
            self._windows.popitem(last=False)
        if len(window) >= limit:
            return ThrottleState(len(window) + 1, _reset_after(window[0], ttl, now))
        window.append(now)
        return ThrottleState(len(window), _reset_after(window[0], ttl, now))

    async def _count_in_sqlite(
        self, database: Database, key: str, ttl: int, limit: int, now: float
    ) -> ThrottleState:
        async with database.transaction() as connection:
            await connection.execute(
                "DELETE FROM throttle_hits WHERE at <= ?", (now - self._max_ttl,)
            )
            await connection.execute(
                "DELETE FROM throttle_hits WHERE key = ? AND at <= ?", (key, now - ttl)
            )
            async with connection.execute(
                "SELECT COUNT(*), MIN(at) FROM throttle_hits WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
            count, oldest = (0, None) if row is None else (row[0], row[1])
            if count >= limit:
                return ThrottleState(count + 1, _reset_after(oldest or now, ttl, now))
            await connection.execute(
                "INSERT INTO throttle_hits (key, at) VALUES (?, ?)", (key, now)
            )
            return ThrottleState(count + 1, _reset_after(oldest or now, ttl, now))


def _reset_after(oldest: float, ttl: int, now: float) -> int:
    """Return the whole seconds until the oldest request leaves the window, 0 to ttl."""
    return max(0, min(ttl, math.ceil(oldest + ttl - now)))
