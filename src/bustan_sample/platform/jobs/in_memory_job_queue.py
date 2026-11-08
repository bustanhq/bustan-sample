import asyncio
from dataclasses import dataclass
from typing import cast

from bustan import ConfigService, Injectable, Logger, LogLevel

from bustan_sample.platform.database import Database

from .job_queue import FailedJob, JobHandler, JobQueue

SHUTDOWN_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class _Registration:
    handler: JobHandler[object]
    max_attempts: int


@dataclass(frozen=True, slots=True)
class _Envelope:
    job: object
    attempt: int = 1


@Injectable()
class InMemoryJobQueue(JobQueue):
    """Runs the jobs on asyncio workers in this process.

    The startup hook starts JOBS_WORKERS workers. A failed job waits
    JOBS_RETRY_DELAY_SECONDS before the second attempt, and two times longer
    before each next attempt. The shutdown hook waits for the queued jobs for
    SHUTDOWN_TIMEOUT_SECONDS, then cancels the remaining work.

    An enqueue in a transaction (Database.transaction()) puts the job in the
    queue after the commit. If the transaction rolls back, the job does not
    run.

    The queue keeps the jobs in memory. Thus the jobs in the queue are lost if
    the process stops. For durable jobs, bind JobQueue to an adapter for a
    durable store.
    """

    def __init__(self, config: ConfigService, database: Database) -> None:
        self._database = database
        self._worker_count = int(config.get("JOBS_WORKERS", 2))
        self._retry_delay = float(config.get("JOBS_RETRY_DELAY_SECONDS", 1.0))
        self._registrations: dict[type, _Registration] = {}
        self._queue: asyncio.Queue[_Envelope] | None = None
        self._workers: list[asyncio.Task[None]] = []
        self._retries: set[asyncio.Task[None]] = set()
        self._failed: list[FailedJob] = []
        self._logger = Logger("JobQueue")

    @property
    def failed(self) -> tuple[FailedJob, ...]:
        return tuple(self._failed)

    def register[J](
        self, job_type: type[J], handler: JobHandler[J], *, max_attempts: int = 3
    ) -> None:
        if job_type in self._registrations:
            raise ValueError(f"a handler for {job_type.__name__} is registered")
        if max_attempts < 1:
            raise ValueError("max_attempts must be 1 or more")
        self._registrations[job_type] = _Registration(
            cast(JobHandler[object], handler), max_attempts
        )

    async def enqueue(self, job: object) -> None:
        if type(job) not in self._registrations:
            raise LookupError(f"no handler is registered for {type(job).__name__}")
        queue = self._started_queue()
        self._database.after_commit(lambda: queue.put_nowait(_Envelope(job)))

    async def on_application_bootstrap(self) -> None:
        # The queue is made here, thus it belongs to the event loop that serves
        # the application.
        self._queue = asyncio.Queue()
        self._workers = [asyncio.create_task(self._work()) for _ in range(self._worker_count)]

    async def on_application_shutdown(self, signal: str | None) -> None:
        if self._queue is None:
            return
        if not await self.drain(SHUTDOWN_TIMEOUT_SECONDS):
            self._logger.record(
                LogLevel.WARN,
                "jobs cancelled at shutdown",
                fields={"queued": self._queue.qsize(), "retries": len(self._retries)},
            )
        tasks = [*self._workers, *self._retries]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._workers = []
        self._queue = None

    async def drain(self, timeout: float | None = None) -> bool:
        """Wait until no job is queued, running or waiting for a retry.

        Return False if the timeout ends first.
        """
        queue = self._started_queue()
        try:
            async with asyncio.timeout(timeout):
                while True:
                    await queue.join()
                    if not self._retries:
                        return True
                    await asyncio.wait(set(self._retries))
        except TimeoutError:
            return False

    def _started_queue(self) -> asyncio.Queue[_Envelope]:
        if self._queue is None:
            raise RuntimeError("the job queue is not started")
        return self._queue

    async def _work(self) -> None:
        queue = self._started_queue()
        while True:
            envelope = await queue.get()
            try:
                await self._run(envelope)
            finally:
                queue.task_done()

    async def _run(self, envelope: _Envelope) -> None:
        registration = self._registrations[type(envelope.job)]
        name = type(envelope.job).__name__
        try:
            await registration.handler(envelope.job)
        # Any error of a job causes a retry, and cannot stop the worker.
        except Exception as exc:  # noqa: BLE001
            if envelope.attempt < registration.max_attempts:
                delay = self._retry_delay * 2 ** (envelope.attempt - 1)
                self._logger.record(
                    LogLevel.WARN,
                    "job failed, retry",
                    fields={
                        "job": name,
                        "attempt": envelope.attempt,
                        "delay_s": delay,
                        "error": repr(exc),
                    },
                )
                retry = _Envelope(envelope.job, envelope.attempt + 1)
                task = asyncio.create_task(self._retry(retry, delay))
                self._retries.add(task)
                task.add_done_callback(self._retries.discard)
                return
            self._failed.append(FailedJob(envelope.job, envelope.attempt, repr(exc)))
            self._logger.record(
                LogLevel.ERROR,
                "job failed on each attempt",
                fields={"job": name, "attempts": envelope.attempt, "error": repr(exc)},
            )
            return
        self._logger.record(
            LogLevel.LOG, "job done", fields={"job": name, "attempt": envelope.attempt}
        )

    async def _retry(self, envelope: _Envelope, delay: float) -> None:
        await asyncio.sleep(delay)
        self._started_queue().put_nowait(envelope)
