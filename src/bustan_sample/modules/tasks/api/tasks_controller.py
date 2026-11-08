from typing import Annotated
from uuid import UUID

from bustan import Auth, Controller, Delete, Get, HttpResponse, Patch, Post, UseFilters

from bustan_sample.modules.identity import STRATEGY, AuthenticatedUser, CurrentUser

from ..application.create_task_command import CreateTaskCommand, CreateTaskHandler
from ..application.delete_task_command import DeleteTaskCommand, DeleteTaskHandler
from ..application.get_task_query import GetTaskHandler, GetTaskQuery
from ..application.list_tasks_query import ListTasksHandler, ListTasksQuery
from ..application.update_task_command import UpdateTaskCommand, UpdateTaskHandler
from ..domain.task import TaskStatus
from .task_errors_filter import TaskErrorsFilter
from .task_schemas import CreateTaskRequest, TaskResponse, UpdateTaskRequest

User = Annotated[AuthenticatedUser, CurrentUser()]


@UseFilters(TaskErrorsFilter())
@Controller("/tasks")
@Auth(STRATEGY)
class TasksController:
    """Maps HTTP requests to commands and queries. It has no business logic.

    Each route needs a token. Each command and query gets the id of the user
    of the token as the owner id.
    """

    def __init__(
        self,
        create_task: CreateTaskHandler,
        update_task: UpdateTaskHandler,
        delete_task: DeleteTaskHandler,
        get_task: GetTaskHandler,
        list_tasks: ListTasksHandler,
    ) -> None:
        self._create_task = create_task
        self._update_task = update_task
        self._delete_task = delete_task
        self._get_task = get_task
        self._list_tasks = list_tasks

    @Get("/")
    async def list_tasks(
        self, user: User, status: TaskStatus | None = None
    ) -> list[dict[str, object]]:
        tasks = await self._list_tasks.execute(
            ListTasksQuery(owner_id=user.user_id, status=status)
        )
        return [TaskResponse.from_task(task).to_json() for task in tasks]

    @Get("/{task_id}")
    async def get_task(self, user: User, task_id: UUID) -> dict[str, object]:
        task = await self._get_task.execute(
            GetTaskQuery(owner_id=user.user_id, task_id=task_id)
        )
        return TaskResponse.from_task(task).to_json()

    @Post("/")
    async def create_task(self, user: User, payload: CreateTaskRequest) -> HttpResponse:
        task = await self._create_task.execute(
            CreateTaskCommand(
                owner_id=user.user_id,
                title=payload.title,
                description=payload.description,
                due_on=payload.due_on,
            )
        )
        return HttpResponse.json(
            TaskResponse.from_task(task).to_json(),
            status_code=201,
            headers={"location": f"/tasks/{task.id}"},
        )

    @Patch("/{task_id}")
    async def update_task(
        self, user: User, task_id: UUID, payload: UpdateTaskRequest
    ) -> dict[str, object]:
        task = await self._update_task.execute(
            UpdateTaskCommand(
                owner_id=user.user_id,
                task_id=task_id,
                title=payload.title,
                description=payload.description,
                status=payload.status,
                due_on=payload.due_on,
                clear_due_on="due_on" in payload.model_fields_set
                and payload.due_on is None,
            )
        )
        return TaskResponse.from_task(task).to_json()

    @Delete("/{task_id}")
    async def delete_task(self, user: User, task_id: UUID) -> None:
        # A handler that returns None answers 204 No Content.
        await self._delete_task.execute(
            DeleteTaskCommand(owner_id=user.user_id, task_id=task_id)
        )
