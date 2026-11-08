from bustan import ClassProvider, Module

from bustan_sample.modules.identity import IdentityModule
from bustan_sample.platform.clock import ClockModule
from bustan_sample.platform.events import EventsModule

from .api.tasks_controller import TasksController
from .application.create_task_command import CreateTaskHandler
from .application.delete_task_command import DeleteTaskHandler
from .application.get_task_query import GetTaskHandler
from .application.list_tasks_query import ListTasksHandler
from .application.on_user_registered import OnUserRegistered
from .application.update_task_command import UpdateTaskHandler
from .domain.task_repository import TaskRepository
from .infra.in_memory_task_repository import InMemoryTaskRepository


# The module binds the storage port of the domain to an adapter of the infra
# layer. To use a database, bind TaskRepository to a different class here.
# IdentityModule gives the authenticator for @Auth("bearer") on the controller.
# OnUserRegistered subscribes to the event of identity in its on_module_init.
@Module(
    imports=[ClockModule, EventsModule, IdentityModule],
    controllers=[TasksController],
    providers=[
        ClassProvider(provide=TaskRepository, use_class=InMemoryTaskRepository),
        CreateTaskHandler,
        UpdateTaskHandler,
        DeleteTaskHandler,
        GetTaskHandler,
        ListTasksHandler,
        OnUserRegistered,
    ],
)
class TasksModule:
    pass
