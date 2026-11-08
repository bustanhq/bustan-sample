import asyncio

from support.fakes import RecordingJobQueue, RecordingMailer

from bustan_sample.modules.identity.jobs.send_welcome_email_job import (
    MAX_ATTEMPTS,
    SUBJECT,
    SendWelcomeEmailHandler,
    SendWelcomeEmailJob,
)


def test_the_handler_registers_with_retries() -> None:
    jobs = RecordingJobQueue()
    SendWelcomeEmailHandler(jobs, RecordingMailer()).on_module_init()
    _, max_attempts = jobs.registered[SendWelcomeEmailJob]
    assert max_attempts == MAX_ATTEMPTS > 1


def test_the_job_sends_the_welcome_email() -> None:
    mailer = RecordingMailer()
    handler = SendWelcomeEmailHandler(RecordingJobQueue(), mailer)
    asyncio.run(handler.run(SendWelcomeEmailJob("user-1", "ada@example.com")))
    [(to, subject, body)] = mailer.sent
    assert (to, subject) == ("ada@example.com", SUBJECT)
    assert body
