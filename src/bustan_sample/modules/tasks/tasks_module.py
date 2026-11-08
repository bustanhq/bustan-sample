from bustan import ClassProvider, FactoryProvider, Module

from bustan_sample.modules.identity import IdentityModule
from bustan_sample.platform.clock import ClockModule
from bustan_sample.platform.database import Database, DatabaseModule
from bustan_sample.platform.events import EventsModule

from .api.tasks_controller import TasksController
from .application.create_task_command import CreateTaskHandler
from .application.delete_task_command import DeleteTaskHandler
from .application.get_task_query import GetTaskHandler
from .application.list_tasks_query import ListTasksHandler
from .application.update_task_command import UpdateTaskHandler
from .domain.recurrence_parser import RecurrenceParser
from .domain.task_repository import TaskRepository
from .infra.in_memory_task_repository import InMemoryTaskRepository
from .infra.rule_based_recurrence_parser import RuleBasedRecurrenceParser
from .infra.sqlite_task_repository import SqliteTaskRepository
from .listeners.on_user_registered import OnUserRegistered


def _task_repository(database: Database) -> TaskRepository:
    if database.is_sqlite:
        return SqliteTaskRepository(database)
    return InMemoryTaskRepository()


# The module binds each port of the domain to an adapter of the infra layer.
# DATABASE_BACKEND selects the adapter of TaskRepository. The factory makes
# only the selected adapter, and bustan runs the hooks of that adapter. To
# parse repeat phrases with a model, bind RecurrenceParser to a model adapter.
# IdentityModule gives the authenticator for @Auth("bearer") on the controller.
# OnUserRegistered subscribes to the event of identity in its on_module_init.
@Module(
    imports=[ClockModule, DatabaseModule, EventsModule, IdentityModule],
    controllers=[TasksController],
    providers=[
        FactoryProvider(
            provide=TaskRepository, use_factory=_task_repository, inject=(Database,)
        ),
        ClassProvider(provide=RecurrenceParser, use_class=RuleBasedRecurrenceParser),
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
