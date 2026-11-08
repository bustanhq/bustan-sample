from bustan import Injectable

from bustan_sample.platform.clock import Clock
from bustan_sample.platform.database import Database, Migration, to_text

from .idempotency_keys import IdempotencyKeys

# Add a migration with the next version for each change. Never edit one.
_V1 = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
);
"""
MIGRATIONS = (Migration(1, "create the table idempotency_keys", _V1),)


@Injectable()
class SqliteIdempotencyKeys(IdempotencyKeys):
    """Keeps the keys in the table idempotency_keys.

    The primary key lets only one INSERT succeed for each key, in all
    processes on the same database file. In a transaction, the INSERT joins
    the transaction. BEGIN IMMEDIATE makes a second transaction wait until
    the first one ends, thus the second add() sees the committed key.

    The table keeps each key. A purge of the keys that are older than the
    longest retry window of the jobs is safe. This sample does not purge.
    """

    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def on_module_init(self) -> None:
        await self._database.migrate("idempotency.keys", MIGRATIONS)

    async def add(self, key: str) -> bool:
        inserted = await self._database.execute(
            "INSERT OR IGNORE INTO idempotency_keys (key, added_at) VALUES (?, ?)",
            (key, to_text(self._clock.now())),
        )
        return inserted == 1

    async def contains(self, key: str) -> bool:
        row = await self._database.fetch_one("SELECT 1 FROM idempotency_keys WHERE key = ?", (key,))
        return row is not None
