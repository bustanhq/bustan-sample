"""Test doubles and helpers that more than one test file uses."""

import time
from collections.abc import Callable
from typing import cast

from bustan import ConfigService

from bustan_sample.platform.database import Database
from bustan_sample.platform.events import EventBus
from bustan_sample.platform.jobs import JobHandler, JobQueue
from bustan_sample.platform.mail import Mailer


class RecordingMailer(Mailer):
    """Keeps each message and its idempotency key in place of a send."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.keys: list[str | None] = []

    async def send(
        self, to: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        self.sent.append((to, subject, body))
        self.keys.append(idempotency_key)


class RecordingJobQueue(JobQueue):
    """Keeps the registrations and the enqueued jobs. It runs no job."""

    def __init__(self) -> None:
        self.registered: dict[type, tuple[JobHandler[object], int]] = {}
        self.enqueued: list[object] = []

    def register[J](
        self, job_type: type[J], handler: JobHandler[J], *, max_attempts: int = 3
    ) -> None:
        self.registered[job_type] = (cast(JobHandler[object], handler), max_attempts)

    async def enqueue(self, job: object) -> None:
        self.enqueued.append(job)


def wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    """Wait until the condition is true, for work that runs in the background."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("the condition did not become true in time")
        time.sleep(0.01)


def memory_event_bus(database: Database | None = None) -> EventBus:
    """Return an event bus for the memory backend, with no job queue.

    Give the Database of the code under test, thus the bus delivers after the
    commit of its transactions.
    """
    return EventBus(RecordingJobQueue(), database or Database(ConfigService({})))
