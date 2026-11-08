from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

type JobHandler[J] = Callable[[J], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class FailedJob:
    """A job that failed on each attempt. The queue keeps it for examination."""

    job: object
    attempts: int
    error: str


class JobQueue(ABC):
    """The port for background jobs.

    A job is a frozen dataclass with JSON-compatible fields (str, int, float,
    bool). Thus an adapter for a durable store, for example SQLite, can
    serialize it with no change to the modules. The name of the job class is
    the type of the job in a durable store, thus each job class has a unique
    name. Register the handler of a job type before the first enqueue of that
    type.
    """

    @abstractmethod
    def register[J](
        self, job_type: type[J], handler: JobHandler[J], *, max_attempts: int = 3
    ) -> None:
        """Use handler for each job of exactly this type.

        If the handler raises an error, the queue tries the job again, until
        max_attempts attempts in total.
        """

    @abstractmethod
    async def enqueue(self, job: object) -> None:
        """Add the job. Raise LookupError if no handler is registered for its type."""
