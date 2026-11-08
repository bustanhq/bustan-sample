from bustan import Injectable

from bustan_sample.modules.identity import UserRegistered
from bustan_sample.platform.events import EventBus

from .create_task_command import CreateTaskCommand, CreateTaskHandler

STARTER_TITLE = "Add your first task"
STARTER_DESCRIPTION = (
    "Change the status of this task to done, or delete it. "
    "Then add the tasks that you want to track."
)


@Injectable()
class OnUserRegistered:
    """Gives each new user a starter task.

    The identity module publishes the event and knows nothing about tasks.
    The tasks module imports only the public event type of identity.
    """

    def __init__(self, events: EventBus, create_task: CreateTaskHandler) -> None:
        self._events = events
        self._create_task = create_task

    def on_module_init(self) -> None:
        self._events.subscribe(UserRegistered, self.handle)

    async def handle(self, event: UserRegistered) -> None:
        await self._create_task.execute(
            CreateTaskCommand(
                owner_id=event.user_id,
                title=STARTER_TITLE,
                description=STARTER_DESCRIPTION,
            )
        )
