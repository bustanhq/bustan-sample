from datetime import datetime, timedelta

from bustan import Injectable

from bustan_sample.platform.clock import Clock
from bustan_sample.platform.database import Database, to_text

from .schedule_lock import ScheduleLock

KEEP_RUNS_FOR = timedelta(days=7)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schedule_runs (
    name TEXT NOT NULL,
    run_at TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    PRIMARY KEY (name, run_at)
);
"""


@Injectable()
class SqliteScheduleLock(ScheduleLock):
    """Claims each run with one row in the table schedule_runs.

    The primary key (name, run_at) lets only one INSERT succeed for each run,
    in all processes on the same database file. Each claim removes the rows
    older than KEEP_RUNS_FOR.
    """

    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def on_module_init(self) -> None:
        await self._database.execute_script(_SCHEMA)

    async def claim(self, name: str, run_at: datetime) -> bool:
        async with self._database.transaction() as connection:
            await connection.execute(
                "DELETE FROM schedule_runs WHERE run_at < ?",
                (to_text(run_at - KEEP_RUNS_FOR),),
            )
            cursor = await connection.execute(
                "INSERT OR IGNORE INTO schedule_runs (name, run_at, claimed_at) "
                "VALUES (?, ?, ?)",
                (name, to_text(run_at), to_text(self._clock.now())),
            )
            return cursor.rowcount == 1
