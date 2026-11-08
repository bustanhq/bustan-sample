import asyncio
from dataclasses import dataclass

import pytest
from bustan import ConfigService

from bustan_sample.platform.database import Database
from bustan_sample.platform.jobs import InMemoryJobQueue


@dataclass(frozen=True)
class Work:
    value: int


def _queue() -> InMemoryJobQueue:
    config = ConfigService({"JOBS_WORKERS": 2, "JOBS_RETRY_DELAY_SECONDS": 0})
    return InMemoryJobQueue(config, Database(ConfigService({})))


def test_an_enqueued_job_runs_on_a_worker() -> None:
    async def scenario() -> None:
        queue, done = _queue(), []

        async def handle(job: Work) -> None:
            done.append(job.value)

        queue.register(Work, handle)
        await queue.on_application_bootstrap()
        await queue.enqueue(Work(1))
        await queue.enqueue(Work(2))
        assert await queue.drain(1)
        assert sorted(done) == [1, 2]
        await queue.on_application_shutdown(None)

    asyncio.run(scenario())


def test_a_failed_job_runs_again_until_it_passes() -> None:
    async def scenario() -> None:
        queue, attempts = _queue(), []

        async def flaky(job: Work) -> None:
            attempts.append(job.value)
            if len(attempts) < 3:
                raise ConnectionError("the service is not available")

        queue.register(Work, flaky, max_attempts=3)
        await queue.on_application_bootstrap()
        await queue.enqueue(Work(5))
        assert await queue.drain(1)
        assert attempts == [5, 5, 5]
        assert queue.failed == ()
        await queue.on_application_shutdown(None)

    asyncio.run(scenario())


def test_a_job_that_fails_on_each_attempt_is_kept_as_failed() -> None:
    async def scenario() -> None:
        queue = _queue()

        async def broken(job: Work) -> None:
            raise ValueError("bad job")

        queue.register(Work, broken, max_attempts=2)
        await queue.on_application_bootstrap()
        await queue.enqueue(Work(9))
        assert await queue.drain(1)
        [failed] = queue.failed
        assert (failed.job, failed.attempts) == (Work(9), 2)
        assert "bad job" in failed.error
        await queue.on_application_shutdown(None)

    asyncio.run(scenario())


def test_shutdown_waits_for_the_queued_jobs() -> None:
    async def scenario() -> None:
        queue, done = _queue(), []

        async def slow(job: Work) -> None:
            await asyncio.sleep(0.02)
            done.append(job.value)

        queue.register(Work, slow)
        await queue.on_application_bootstrap()
        for value in range(4):
            await queue.enqueue(Work(value))
        await queue.on_application_shutdown(None)
        assert sorted(done) == [0, 1, 2, 3]

    asyncio.run(scenario())


def test_registration_errors_are_refused() -> None:
    async def scenario() -> None:
        queue = _queue()

        async def handle(job: Work) -> None:
            return None

        queue.register(Work, handle)
        with pytest.raises(ValueError):
            queue.register(Work, handle)
        with pytest.raises(ValueError):
            _queue().register(Work, handle, max_attempts=0)
        await queue.on_application_bootstrap()
        with pytest.raises(LookupError):
            await queue.enqueue("a job type with no handler")
        await queue.on_application_shutdown(None)

    asyncio.run(scenario())


def test_a_job_runs_only_after_its_transaction_commits() -> None:
    async def scenario() -> None:
        database = Database(ConfigService({}))
        queue = InMemoryJobQueue(ConfigService({"JOBS_RETRY_DELAY_SECONDS": 0}), database)
        done: list[int] = []

        async def handle(job: Work) -> None:
            done.append(job.value)

        queue.register(Work, handle)
        await queue.on_application_bootstrap()
        with pytest.raises(ValueError):
            async with database.transaction():
                await queue.enqueue(Work(1))
                raise ValueError("stop")
        async with database.transaction():
            await queue.enqueue(Work(2))
            await asyncio.sleep(0.01)
            assert done == []
        assert await queue.drain(1)
        assert done == [2]
        await queue.on_application_shutdown(None)

    asyncio.run(scenario())
