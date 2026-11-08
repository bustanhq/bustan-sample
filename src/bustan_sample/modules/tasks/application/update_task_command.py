from dataclasses import dataclass
from datetime import date
from uuid import UUID

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.errors import TaskNotFoundError
from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class UpdateTaskCommand:
    """A field that is None does not change. Set clear_due_on to remove the due date."""

    owner_id: UUID
    task_id: UUID
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_on: date | None = None
    clear_due_on: bool = False


@Injectable()
class UpdateTaskHandler:
    def __init__(self, repository: TaskRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: UpdateTaskCommand) -> Task:
        task = await self._repository.get(command.owner_id, command.task_id)
        if task is None:
            raise TaskNotFoundError(command.task_id)
        now = self._clock.now()
        if command.title is not None:
            task.rename(command.title, now)
        if command.description is not None:
            task.describe(command.description, now)
        if command.status is not None:
            task.move_to(command.status, now)
        if command.clear_due_on:
            task.reschedule(None, now)
        elif command.due_on is not None:
            task.reschedule(command.due_on, now)
        await self._repository.save(task)
        return task
