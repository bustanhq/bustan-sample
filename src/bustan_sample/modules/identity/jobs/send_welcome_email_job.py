from dataclasses import dataclass

from bustan import Injectable

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
    """Sends the welcome email. The job queue tries again if the send fails."""

    def __init__(self, jobs: JobQueue, mailer: Mailer) -> None:
        self._jobs = jobs
        self._mailer = mailer

    def on_module_init(self) -> None:
        self._jobs.register(SendWelcomeEmailJob, self.run, max_attempts=MAX_ATTEMPTS)

    async def run(self, job: SendWelcomeEmailJob) -> None:
        await self._mailer.send(job.email, SUBJECT, BODY)
