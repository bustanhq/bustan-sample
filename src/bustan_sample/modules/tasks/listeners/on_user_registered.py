from bustan import Injectable

from bustan_sample.modules.identity import UserRegistered
from bustan_sample.platform.database import Database
from bustan_sample.platform.events import EventBus
from bustan_sample.platform.idempotency import IdempotencyKeys

from ..application.create_task_command import CreateTaskCommand, CreateTaskHandler

STARTER_TITLE = "Add your first task"
STARTER_DESCRIPTION = (
    "Change the status of this task to done, or delete it. "
    "Then add the tasks that you want to track."
)


@Injectable()
class OnUserRegistered:
    """Gives each new user one starter task.

    The identity module publishes the event and knows nothing about tasks.
    The tasks module imports only the public event type of identity.

    A delivery can run more than one time for one event. The idempotency key
    and the task commit in one transaction, thus each user gets one starter
    task.
    """

    def __init__(
        self,
        events: EventBus,
        create_task: CreateTaskHandler,
        database: Database,
        keys: IdempotencyKeys,
    ) -> None:
        self._events = events
        self._create_task = create_task
        self._database = database
        self._keys = keys

    def on_module_init(self) -> None:
        self._events.subscribe(UserRegistered, self.handle)

    async def handle(self, event: UserRegistered) -> None:
        async with self._database.transaction():
            if not await self._keys.add(f"tasks.starter_task:{event.user_id}"):
                return
            await self._create_task.execute(
                CreateTaskCommand(
                    owner_id=event.user_id,
                    title=STARTER_TITLE,
                    description=STARTER_DESCRIPTION,
                )
            )
