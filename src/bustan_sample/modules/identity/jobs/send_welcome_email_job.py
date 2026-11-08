from dataclasses import dataclass

from bustan import Injectable

from bustan_sample.platform.idempotency import IdempotencyKeys
from bustan_sample.platform.jobs import JobQueue
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
    it too. The key goes in after the send: a failed send leaves no key, thus
    the retry sends. If the process stops between the send and the key, the
    user gets the email two times. That is the only case.
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
        await self._mailer.send(job.email, SUBJECT, BODY)
        await self._keys.add(key)
