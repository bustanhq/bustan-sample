import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from support.fakes import RecordingJobQueue

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.jobs import JobScheduler

START = datetime(2026, 1, 1, 9, 3, tzinfo=UTC)


@dataclass(frozen=True)
class Tick:
    pass


def test_a_schedule_enqueues_at_each_agreeing_time_after_the_start() -> None:
    async def scenario() -> None:
        queue = RecordingJobQueue()
        scheduler = JobScheduler(queue, FixedClock(START))
        scheduler.schedule("every-10-minutes", "*/10 * * * *", Tick)
        assert await scheduler.tick(START) == []
        assert await scheduler.tick(START + timedelta(minutes=6)) == []
        assert await scheduler.tick(START + timedelta(minutes=7)) == [
            "every-10-minutes"
        ]
        assert await scheduler.tick(START + timedelta(minutes=8)) == []
        assert await scheduler.tick(START + timedelta(minutes=17)) == [
            "every-10-minutes"
        ]
        assert queue.enqueued == [Tick(), Tick()]

    asyncio.run(scenario())


def test_missed_runs_enqueue_one_job_only() -> None:
    async def scenario() -> None:
        queue = RecordingJobQueue()
        scheduler = JobScheduler(queue, FixedClock(START))
        scheduler.schedule("every-10-minutes", "*/10 * * * *", Tick)
        await scheduler.tick(START)
        await scheduler.tick(START + timedelta(hours=1))
        assert queue.enqueued == [Tick()]

    asyncio.run(scenario())


def test_an_invalid_or_duplicate_schedule_is_refused() -> None:
    scheduler = JobScheduler(RecordingJobQueue(), FixedClock(START))
    with pytest.raises(ValueError, match="not valid"):
        scheduler.schedule("bad", "every ten minutes", Tick)
    scheduler.schedule("daily", "0 7 * * *", Tick)
    with pytest.raises(ValueError, match="exists"):
        scheduler.schedule("daily", "0 8 * * *", Tick)
