import asyncio
import contextlib
import dataclasses
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from bustan import ConfigService, Injectable, Logger, LogLevel

from bustan_sample.platform.clock import Clock
from bustan_sample.platform.database import Database, Migration, to_text

from .job_queue import FailedJob, JobHandler, JobQueue

SHUTDOWN_TIMEOUT_SECONDS = 10.0

# Add a migration with the next version for each change. Never edit one.
_V1 = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    run_after TEXT NOT NULL,
    locked_until TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_ready ON jobs (status, run_after);
"""
MIGRATIONS = (Migration(1, "create the table jobs", _V1),)


@dataclass(frozen=True, slots=True)
class _Registration:
    job_type: type
    handler: JobHandler[object]
    max_attempts: int


@Injectable()
class SqliteJobQueue(JobQueue):
    """Keeps the jobs in the table jobs of the SQLite database.

    A job stays in the table until it ends. Thus a job survives a restart, and
    all processes on the same database file share the jobs. A worker claims a
    job with one UPDATE statement, thus two workers never get the same job.

    A claim has a lease of JOBS_LEASE_SECONDS. If the process stops before
    the job ends, a worker takes the job again after the lease. Thus a handler
    can run more than one time for one job, and must give the same result each
    time. A done job is deleted. A job that fails on each attempt stays in the
    table with the status failed.

    An enqueue in a transaction (Database.transaction()) joins it: the job
    commits with the data of the transaction, or not at all. Thus a job is
    never lost between a save and an enqueue. After the commit, or immediately
    outside a transaction, the enqueue starts a worker of this process. A
    worker looks for the jobs of other processes each JOBS_POLL_SECONDS. A
    process claims only the job types that it registered.
    """

    def __init__(self, database: Database, config: ConfigService, clock: Clock) -> None:
        self._database = database
        self._clock = clock
        self._worker_count = int(config.get("JOBS_WORKERS", 2))
        self._retry_delay = float(config.get("JOBS_RETRY_DELAY_SECONDS", 1.0))
        self._poll = float(config.get("JOBS_POLL_SECONDS", 0.5))
        self._lease = timedelta(seconds=float(config.get("JOBS_LEASE_SECONDS", 300)))
        self._registrations: dict[str, _Registration] = {}
        self._workers: list[asyncio.Task[None]] = []
        self._busy = 0
        self._stopping = False
        self._wake: asyncio.Event | None = None
        self._logger = Logger("JobQueue")

    def register[J](
        self, job_type: type[J], handler: JobHandler[J], *, max_attempts: int = 3
    ) -> None:
        name = job_type.__name__
        if not dataclasses.is_dataclass(job_type):
            raise ValueError(f"{name} must be a dataclass, thus the queue can store it")
        if name in self._registrations:
            raise ValueError(f"a handler for {name} is registered")
        if max_attempts < 1:
            raise ValueError("max_attempts must be 1 or more")
        self._registrations[name] = _Registration(
            job_type, cast(JobHandler[object], handler), max_attempts
        )

    async def enqueue(self, job: object) -> None:
        name = type(job).__name__
        registration = self._registrations.get(name)
        if registration is None or registration.job_type is not type(job):
            raise LookupError(f"no handler is registered for {name}")
        now = to_text(self._clock.now())
        # register() accepts only dataclasses, thus the cast is safe.
        payload = json.dumps(dataclasses.asdict(cast(Any, job)))
        await self._database.execute(
            "INSERT INTO jobs (type, payload, attempt, status, run_after, created_at) "
            "VALUES (?, ?, 1, 'queued', ?, ?)",
            (name, payload, now, now),
        )
        # A worker that started before the commit cannot see the row.
        self._database.after_commit(self._wake_workers)

    def _wake_workers(self) -> None:
        if self._wake is not None:
            self._wake.set()

    async def failed_jobs(self) -> list[FailedJob]:
        rows = await self._database.fetch_all(
            "SELECT type, payload, attempt, error FROM jobs WHERE status = 'failed' ORDER BY id"
        )
        return [
            FailedJob(self._load(row["type"], row["payload"]), row["attempt"], row["error"])
            for row in rows
            if row["type"] in self._registrations
        ]

    async def on_module_init(self) -> None:
        await self._database.migrate("jobs.queue", MIGRATIONS)

    async def on_application_bootstrap(self) -> None:
        self._stopping = False
        self._wake = asyncio.Event()
        self._workers = [asyncio.create_task(self._work()) for _ in range(self._worker_count)]

    async def on_application_shutdown(self, signal: str | None) -> None:
        # The workers claim no new job. The queued jobs stay in the table for
        # the next start. The shutdown waits for the jobs that run.
        self._stopping = True
        if self._wake is not None:
            self._wake.set()
        try:
            async with asyncio.timeout(SHUTDOWN_TIMEOUT_SECONDS):
                while self._busy:
                    await asyncio.sleep(0.01)
        except TimeoutError:
            self._logger.record(
                LogLevel.WARN,
                "jobs cancelled at shutdown",
                fields={"running": self._busy},
            )
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def drain(self, timeout: float | None = None) -> bool:
        """Wait until no job of a registered type is due or runs in this process.

        Return False if the timeout ends first.
        """
        try:
            async with asyncio.timeout(timeout):
                while self._busy or await self._has_due_jobs():
                    await asyncio.sleep(min(self._poll, 0.02))
        except TimeoutError:
            return False
        return True

    async def _work(self) -> None:
        wake = self._wake
        if wake is None:
            raise RuntimeError("the job queue is not started")
        while not self._stopping:
            wake.clear()
            # _busy counts the claim too. Thus drain() never sees a claimed job
            # that is in no counter and no longer queued.
            self._busy += 1
            claimed = None
            try:
                claimed = await self._claim()
                if claimed is not None:
                    await self._run(*claimed)
            # A database error must not stop the worker. A claimed job that did
            # not end runs again after its lease.
            except Exception as exc:  # noqa: BLE001
                self._logger.record(LogLevel.ERROR, "job worker error", fields={"error": repr(exc)})
            finally:
                self._busy -= 1
            if claimed is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(wake.wait(), self._poll)

    async def _claim(self) -> tuple[int, str, str, int] | None:
        if not self._registrations:
            return None
        now = self._clock.now()
        types = list(self._registrations)
        placeholders = ", ".join("?" for _ in types)
        rows = await self._database.fetch_all(
            f"""
            UPDATE jobs SET status = 'running', locked_until = ?
            WHERE id = (
                SELECT id FROM jobs
                WHERE type IN ({placeholders})
                  AND ((status = 'queued' AND run_after <= ?)
                       OR (status = 'running' AND locked_until < ?))
                ORDER BY run_after, id
                LIMIT 1
            )
            RETURNING id, type, payload, attempt
            """,
            [to_text(now + self._lease), *types, to_text(now), to_text(now)],
        )
        if not rows:
            return None
        row = rows[0]
        return row["id"], row["type"], row["payload"], row["attempt"]

    async def _run(self, job_id: int, name: str, payload: str, attempt: int) -> None:
        registration = self._registrations[name]
        try:
            await registration.handler(self._load(name, payload))
        # Any error of a job causes a retry, and cannot stop the worker.
        except Exception as exc:  # noqa: BLE001
            await self._fail(job_id, name, attempt, registration.max_attempts, exc)
            return
        await self._database.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self._logger.record(LogLevel.LOG, "job done", fields={"job": name, "attempt": attempt})

    async def _fail(
        self, job_id: int, name: str, attempt: int, max_attempts: int, exc: Exception
    ) -> None:
        if attempt < max_attempts:
            delay = self._retry_delay * 2 ** (attempt - 1)
            run_after = to_text(self._clock.now() + timedelta(seconds=delay))
            await self._database.execute(
                "UPDATE jobs SET status = 'queued', attempt = attempt + 1, run_after = ?, "
                "locked_until = NULL, error = ? WHERE id = ?",
                (run_after, repr(exc), job_id),
            )
            self._logger.record(
                LogLevel.WARN,
                "job failed, retry",
                fields={
                    "job": name,
                    "attempt": attempt,
                    "delay_s": delay,
                    "error": repr(exc),
                },
            )
            return
        await self._database.execute(
            "UPDATE jobs SET status = 'failed', locked_until = NULL, error = ? WHERE id = ?",
            (repr(exc), job_id),
        )
        self._logger.record(
            LogLevel.ERROR,
            "job failed on each attempt",
            fields={"job": name, "attempts": attempt, "error": repr(exc)},
        )

    async def _has_due_jobs(self) -> bool:
        if not self._registrations:
            return False
        now = to_text(self._clock.now())
        types = list(self._registrations)
        placeholders = ", ".join("?" for _ in types)
        row = await self._database.fetch_one(
            f"SELECT 1 FROM jobs WHERE type IN ({placeholders}) "
            "AND ((status = 'queued' AND run_after <= ?) "
            "OR (status = 'running' AND locked_until < ?)) LIMIT 1",
            [*types, now, now],
        )
        return row is not None

    def _load(self, name: str, payload: str) -> object:
        return self._registrations[name].job_type(**json.loads(payload))
