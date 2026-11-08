import asyncio

import pytest

from bustan_sample.modules.identity.jobs.send_welcome_email_job import (
    MAX_ATTEMPTS,
    SUBJECT,
    SendWelcomeEmailHandler,
    SendWelcomeEmailJob,
)
from bustan_sample.platform.idempotency import InMemoryIdempotencyKeys

from support.database import memory_database
from support.fakes import RecordingJobQueue, RecordingMailer

JOB = SendWelcomeEmailJob("user-1", "ada@example.com")


def _handler(
    mailer: RecordingMailer, jobs: RecordingJobQueue | None = None
) -> SendWelcomeEmailHandler:
    keys = InMemoryIdempotencyKeys(memory_database())
    return SendWelcomeEmailHandler(jobs or RecordingJobQueue(), mailer, keys)


class _FlakyMailer(RecordingMailer):
    """Fails on the first send."""

    async def send(self, to: str, subject: str, body: str) -> None:
        if not hasattr(self, "failed"):
            self.failed = True
            raise ConnectionError("the mail server is down")
        await super().send(to, subject, body)


def test_the_handler_registers_with_retries() -> None:
    jobs = RecordingJobQueue()
    _handler(RecordingMailer(), jobs).on_module_init()
    _, max_attempts = jobs.registered[SendWelcomeEmailJob]
    assert max_attempts == MAX_ATTEMPTS > 1


def test_the_job_sends_the_welcome_email() -> None:
    mailer = RecordingMailer()
    asyncio.run(_handler(mailer).run(JOB))
    [(to, subject, body)] = mailer.sent
    assert (to, subject) == ("ada@example.com", SUBJECT)
    assert body


def test_a_second_run_of_the_job_sends_no_second_email() -> None:
    async def scenario() -> None:
        mailer = RecordingMailer()
        handler = _handler(mailer)
        await handler.run(JOB)
        await handler.run(JOB)
        assert len(mailer.sent) == 1

    asyncio.run(scenario())


def test_a_failed_send_leaves_no_key_thus_the_retry_sends() -> None:
    async def scenario() -> None:
        mailer = _FlakyMailer()
        handler = _handler(mailer)
        with pytest.raises(ConnectionError):
            await handler.run(JOB)
        await handler.run(JOB)
        assert len(mailer.sent) == 1

    asyncio.run(scenario())
