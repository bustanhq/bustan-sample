import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from bustan import ConfigService

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.jobs import InMemoryScheduleLock, JobScheduler, ScheduleLock

from support.fakes import RecordingJobQueue

START = datetime(2026, 1, 1, 9, 3, tzinfo=UTC)


@dataclass(frozen=True)
class Tick:
    pass


def _scheduler(
    queue: RecordingJobQueue,
    lock: ScheduleLock | None = None,
    **config: object,
) -> JobScheduler:
    return JobScheduler(
        queue, FixedClock(START), lock or InMemoryScheduleLock(), ConfigService(config)
    )


def test_a_schedule_enqueues_at_each_agreeing_time_after_the_start() -> None:
    async def scenario() -> None:
        queue = RecordingJobQueue()
        scheduler = _scheduler(queue)
        scheduler.schedule("every-10-minutes", "*/10 * * * *", Tick)
        assert await scheduler.tick(START) == []
        assert await scheduler.tick(START + timedelta(minutes=6)) == []
        assert await scheduler.tick(START + timedelta(minutes=7)) == ["every-10-minutes"]
        assert await scheduler.tick(START + timedelta(minutes=8)) == []
        assert await scheduler.tick(START + timedelta(minutes=17)) == ["every-10-minutes"]
        assert queue.enqueued == [Tick(), Tick()]

    asyncio.run(scenario())


def test_missed_runs_enqueue_one_job_only() -> None:
    async def scenario() -> None:
        queue = RecordingJobQueue()
        scheduler = _scheduler(queue)
        scheduler.schedule("every-10-minutes", "*/10 * * * *", Tick)
        await scheduler.tick(START)
        await scheduler.tick(START + timedelta(hours=1))
        assert queue.enqueued == [Tick()]

    asyncio.run(scenario())


def test_two_schedulers_with_one_lock_enqueue_each_run_one_time() -> None:
    async def scenario() -> None:
        queue, lock = RecordingJobQueue(), InMemoryScheduleLock()
        first, second = _scheduler(queue, lock), _scheduler(queue, lock)
        for scheduler in (first, second):
            scheduler.schedule("every-10-minutes", "*/10 * * * *", Tick)
            await scheduler.tick(START)
        due = START + timedelta(minutes=7)
        claimed = await first.tick(due) + await second.tick(due)
        assert claimed == ["every-10-minutes"]
        assert queue.enqueued == [Tick()]

    asyncio.run(scenario())


def test_a_disabled_scheduler_starts_no_loop() -> None:
    async def scenario() -> None:
        scheduler = _scheduler(RecordingJobQueue(), JOBS_SCHEDULER_ENABLED="false")
        scheduler.schedule("daily", "0 7 * * *", Tick)
        await scheduler.on_application_bootstrap()
        assert scheduler.enabled is False
        assert scheduler._loop_task is None
        await scheduler.on_application_shutdown(None)

    asyncio.run(scenario())


def test_an_invalid_or_duplicate_schedule_is_refused() -> None:
    scheduler = _scheduler(RecordingJobQueue())
    with pytest.raises(ValueError, match="not valid"):
        scheduler.schedule("bad", "every ten minutes", Tick)
    scheduler.schedule("daily", "0 7 * * *", Tick)
    with pytest.raises(ValueError, match="exists"):
        scheduler.schedule("daily", "0 8 * * *", Tick)
