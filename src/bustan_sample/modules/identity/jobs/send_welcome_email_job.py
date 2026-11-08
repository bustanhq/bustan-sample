from dataclasses import dataclass

from bustan import Injectable

from bustan_sample.platform.http import ExternalServiceError
from bustan_sample.platform.idempotency import IdempotencyKeys
from bustan_sample.platform.jobs import JobQueue, PermanentJobError, RetryJobLater
from bustan_sample.platform.mail import Mailer

MAX_ATTEMPTS = 5
SUBJECT = "Welcome to bustan-sample"
BODY = (
    "Your account is ready.\n\n"
    "Log in with your email address and your password to manage your tasks.\n"
)


@dataclass(frozen=True, slots=True)
class SendWelcomeEmailJob:
    user_id: str
    email: str


@Injectable()
class SendWelcomeEmailHandler:
    """Sends the welcome email one time. The job queue tries again if the send fails.

    The job can run more than one time, and the event delivery that enqueues
    it too. The local key goes in after the send: a failed send leaves no key,
    thus the retry sends. The mailer also gets the key. A provider that
    accepts it, for example Resend, sends no second email if the process stops
    between the send and the local key.

    The handler tells the queue what a failure means. An error that a retry
    cannot repair fails the job at once. A Retry-After of the provider sets
    the wait before the next attempt.
    """

    def __init__(self, jobs: JobQueue, mailer: Mailer, keys: IdempotencyKeys) -> None:
        self._jobs = jobs
        self._mailer = mailer
        self._keys = keys

    def on_module_init(self) -> None:
        self._jobs.register(SendWelcomeEmailJob, self.run, max_attempts=MAX_ATTEMPTS)

    async def run(self, job: SendWelcomeEmailJob) -> None:
        key = f"identity.welcome_email:{job.user_id}"
        if await self._keys.contains(key):
            return
        try:
            await self._mailer.send(job.email, SUBJECT, BODY, idempotency_key=key)
        except ExternalServiceError as exc:
            if not exc.retryable:
                raise PermanentJobError(str(exc)) from exc
            if exc.retry_after is not None:
                raise RetryJobLater(exc.retry_after, str(exc)) from exc
            raise
        await self._keys.add(key)
