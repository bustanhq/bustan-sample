import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from bustan import ConfigService, Injectable, Logger, LogLevel
from croniter import croniter

from bustan_sample.platform.clock import Clock

from .job_queue import JobQueue
from .schedule_lock import ScheduleLock

MIN_SLEEP_SECONDS = 1.0
MAX_SLEEP_SECONDS = 60.0


@dataclass(slots=True)
class _Schedule:
    name: str
    cron: str
    make_job: Callable[[], object]
    next_run: datetime | None = None


@Injectable()
class JobScheduler:
    """Enqueues a job each time that its cron expression agrees with the time.

    The expressions use UTC. A schedule runs first at the next agreeing time
    after the startup. If the process misses runs, the next tick enqueues one
    job only, not one job for each missed run.

    With more than one process, the ScheduleLock lets only one process enqueue
    each run. JOBS_SCHEDULER_ENABLED=false stops the scheduler loop in a
    process, for a deployment with one scheduler process.
    """

    def __init__(
        self, queue: JobQueue, clock: Clock, lock: ScheduleLock, config: ConfigService
    ) -> None:
        self._queue = queue
        self._clock = clock
        self._lock = lock
        self.enabled = _as_bool(config.get("JOBS_SCHEDULER_ENABLED", True))
        self._schedules: dict[str, _Schedule] = {}
        self._loop_task: asyncio.Task[None] | None = None
        self._logger = Logger("JobScheduler")

    def schedule(self, name: str, cron: str, make_job: Callable[[], object]) -> None:
        """Enqueue make_job() on the cron expression. Raise ValueError if it is not valid."""
        if name in self._schedules:
            raise ValueError(f"a schedule with the name {name!r} exists")
        if not croniter.is_valid(cron):
            raise ValueError(f"the cron expression of {name!r} is not valid: {cron!r}")
        self._schedules[name] = _Schedule(name, cron, make_job)

    async def tick(self, now: datetime) -> list[str]:
        """Enqueue the job of each schedule that is due at the time now.

        Return the names of the schedules that enqueued a job. A due run that
        a different process claimed first enqueues nothing here.
        """
        enqueued: list[str] = []
        for schedule in self._schedules.values():
            if schedule.next_run is None:
                schedule.next_run = _next_run(schedule.cron, now)
                continue
            if schedule.next_run > now:
                continue
            run_at = schedule.next_run
            schedule.next_run = _next_run(schedule.cron, now)
            if await self._lock.claim(schedule.name, run_at):
                await self._queue.enqueue(schedule.make_job())
                enqueued.append(schedule.name)
        return enqueued

    async def on_application_bootstrap(self) -> None:
        if not self.enabled:
            self._logger.record(
                LogLevel.LOG,
                "scheduler off in this process",
                fields={"schedules": len(self._schedules)},
            )
            return
        self._loop_task = asyncio.create_task(self._loop())

    async def on_application_shutdown(self, signal: str | None) -> None:
        if self._loop_task is not None:
            self._loop_task.cancel()
            await asyncio.gather(self._loop_task, return_exceptions=True)
            self._loop_task = None

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick(self._clock.now())
            # An error of the lock or the queue must not stop the schedules.
            except Exception as exc:  # noqa: BLE001
                self._logger.record(
                    LogLevel.ERROR, "scheduler tick failed", fields={"error": repr(exc)}
                )
            await asyncio.sleep(self._seconds_to_next_run())

    def _seconds_to_next_run(self) -> float:
        now = self._clock.now()
        runs = [s.next_run for s in self._schedules.values() if s.next_run is not None]
        if not runs:
            return MAX_SLEEP_SECONDS
        seconds = (min(runs) - now).total_seconds()
        return min(max(seconds, MIN_SLEEP_SECONDS), MAX_SLEEP_SECONDS)


def _next_run(cron: str, after: datetime) -> datetime:
    return croniter(cron, after).get_next(datetime)


def _as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
