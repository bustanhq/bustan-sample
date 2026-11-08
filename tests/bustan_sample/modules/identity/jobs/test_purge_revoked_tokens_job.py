import asyncio
from datetime import timedelta

from bustan import ConfigService

from bustan_sample.modules.identity.infra.in_memory_revoked_token_repository import (
    InMemoryRevokedTokenRepository,
)
from bustan_sample.modules.identity.jobs.purge_revoked_tokens_job import (
    PurgeRevokedTokensHandler,
    PurgeRevokedTokensJob,
)
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.jobs import InMemoryScheduleLock, JobScheduler

from support.fakes import RecordingJobQueue


class _Setup:
    def __init__(self) -> None:
        self.clock = FixedClock()
        self.jobs = RecordingJobQueue()
        self.scheduler = JobScheduler(
            self.jobs, self.clock, InMemoryScheduleLock(), ConfigService({})
        )
        self.revoked = InMemoryRevokedTokenRepository()
        self.handler = PurgeRevokedTokensHandler(
            self.jobs, self.scheduler, self.revoked, self.clock
        )


def test_the_job_is_registered_and_scheduled_each_10_minutes() -> None:
    async def scenario() -> None:
        setup = _Setup()
        setup.handler.on_module_init()
        assert PurgeRevokedTokensJob in setup.jobs.registered
        start = setup.clock.now()
        await setup.scheduler.tick(start)
        await setup.scheduler.tick(start + timedelta(minutes=10))
        await setup.scheduler.tick(start + timedelta(minutes=20))
        assert setup.jobs.enqueued == [PurgeRevokedTokensJob(), PurgeRevokedTokensJob()]

    asyncio.run(scenario())


def test_the_job_removes_the_entries_of_expired_tokens() -> None:
    async def scenario() -> None:
        setup = _Setup()
        now = setup.clock.now()
        await setup.revoked.revoke("expired", now - timedelta(minutes=1))
        await setup.revoked.revoke("valid", now + timedelta(minutes=10))
        await setup.handler.run(PurgeRevokedTokensJob())
        assert await setup.revoked.is_revoked("expired") is False
        assert await setup.revoked.is_revoked("valid") is True

    asyncio.run(scenario())
