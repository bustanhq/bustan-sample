from bustan import Injectable

from bustan_sample.platform.events import EventBus
from bustan_sample.platform.jobs import JobQueue

from ..domain.events import UserRegistered
from ..jobs.send_welcome_email_job import SendWelcomeEmailJob


@Injectable()
class OnUserRegistered:
    """Enqueues the welcome email for a new user.

    The handler does not send the email itself. A send can fail, and the job
    queue tries a failed job again.
    """

    def __init__(self, events: EventBus, jobs: JobQueue) -> None:
        self._events = events
        self._jobs = jobs

    def on_module_init(self) -> None:
        self._events.subscribe(UserRegistered, self.handle)

    async def handle(self, event: UserRegistered) -> None:
        await self._jobs.enqueue(
            SendWelcomeEmailJob(user_id=str(event.user_id), email=event.email)
        )
