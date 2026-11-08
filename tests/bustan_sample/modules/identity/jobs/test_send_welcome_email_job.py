import asyncio

import pytest

from bustan_sample.modules.identity.jobs.send_welcome_email_job import (
    MAX_ATTEMPTS,
    SUBJECT,
    SendWelcomeEmailHandler,
    SendWelcomeEmailJob,
)
from bustan_sample.platform.http import ExternalServiceError
from bustan_sample.platform.idempotency import InMemoryIdempotencyKeys
from bustan_sample.platform.jobs import PermanentJobError, RetryJobLater

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

    async def send(
        self, to: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        if not hasattr(self, "failed"):
            self.failed = True
            raise ConnectionError("the mail server is down")
        await super().send(to, subject, body, idempotency_key=idempotency_key)


class _FailingMailer(RecordingMailer):
    """Raises the given error on each send."""

    def __init__(self, error: ExternalServiceError) -> None:
        super().__init__()
        self.error = error

    async def send(
        self, to: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        raise self.error


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


def test_the_job_gives_its_key_to_the_mailer() -> None:
    mailer = RecordingMailer()
    asyncio.run(_handler(mailer).run(JOB))
    assert mailer.keys == ["identity.welcome_email:user-1"]


def test_an_error_that_a_retry_cannot_repair_fails_the_job_at_once() -> None:
    error = ExternalServiceError("resend", "POST /emails gave 422", retryable=False, status=422)
    with pytest.raises(PermanentJobError, match="422"):
        asyncio.run(_handler(_FailingMailer(error)).run(JOB))


def test_a_retry_after_of_the_provider_sets_the_wait() -> None:
    error = ExternalServiceError("resend", "429", retryable=True, retry_after=12.0)
    with pytest.raises(RetryJobLater) as caught:
        asyncio.run(_handler(_FailingMailer(error)).run(JOB))
    assert caught.value.after_seconds == 12.0


def test_a_retryable_error_with_no_wait_goes_to_the_usual_retry() -> None:
    error = ExternalServiceError("resend", "timeout", retryable=True)
    with pytest.raises(ExternalServiceError):
        asyncio.run(_handler(_FailingMailer(error)).run(JOB))
