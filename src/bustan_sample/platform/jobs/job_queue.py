from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

type JobHandler[J] = Callable[[J], Awaitable[None]]

# The longest wait before one retry, also when a handler asks for more.
MAX_RETRY_DELAY_SECONDS = 3600.0


class PermanentJobError(Exception):
    """Raise it in a job handler when a retry cannot succeed.

    The queue does not try the job again: the job fails at once, and the
    queue keeps it as failed. Examples: the external service refused the
    request as not valid, or the data of the job is gone.
    """


class RetryJobLater(Exception):
    """Raise it in a job handler to set the wait before the next attempt.

    The queue waits after_seconds, or the usual delay if that is longer, and
    never more than MAX_RETRY_DELAY_SECONDS. The attempt counts against
    max_attempts. Example: an external service sent Retry-After.
    """

    def __init__(self, after_seconds: float, message: str = "") -> None:
        super().__init__(message or f"retry after {after_seconds} s")
        self.after_seconds = after_seconds


def next_retry_delay(
    error: Exception, attempt: int, max_attempts: int, base_delay: float
) -> float | None:
    """Return the wait in seconds before the next attempt, or None if the job fails now.

    The usual delay is base_delay before the second attempt, and two times
    longer before each next attempt.
    """
    if isinstance(error, PermanentJobError) or attempt >= max_attempts:
        return None
    delay = base_delay * 2 ** (attempt - 1)
    if isinstance(error, RetryJobLater):
        delay = max(delay, error.after_seconds)
    return min(delay, MAX_RETRY_DELAY_SECONDS)


def failure_message(error: Exception) -> str:
    """Return the log message for a job that fails with no next attempt."""
    if isinstance(error, PermanentJobError):
        return "job failed, no retry"
    return "job failed on each attempt"


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
        max_attempts attempts in total. PermanentJobError stops the retries,
        and RetryJobLater sets the wait.
        """

    @abstractmethod
    async def enqueue(self, job: object) -> None:
        """Add the job. Raise LookupError if no handler is registered for its type."""
