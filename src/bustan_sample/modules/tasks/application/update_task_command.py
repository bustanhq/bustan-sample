from dataclasses import dataclass
from datetime import date
from uuid import UUID

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.errors import TaskNotFoundError
from ..domain.recurrence_parser import RecurrenceParser
from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class UpdateTaskCommand:
    """A field that is None does not change.

    Set clear_due_on to remove the due date, and clear_repeat to stop the
    recurrence.
    """

    owner_id: UUID
    task_id: UUID
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_on: date | None = None
    clear_due_on: bool = False
    repeat: str | None = None
    clear_repeat: bool = False


@Injectable()
class UpdateTaskHandler:
    """Changes a task. When a recurring task becomes done, adds the next task."""

    def __init__(
        self, repository: TaskRepository, clock: Clock, parser: RecurrenceParser
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._parser = parser

    async def execute(self, command: UpdateTaskCommand) -> Task:
        task = await self._repository.get(command.owner_id, command.task_id)
        if task is None:
            raise TaskNotFoundError(command.task_id)
        recurrence = (
            None if command.repeat is None else await self._parser.parse(command.repeat)
        )
        was_done = task.status is TaskStatus.DONE
        now = self._clock.now()
        if command.title is not None:
            task.rename(command.title, now)
        if command.description is not None:
            task.describe(command.description, now)
        # The sequence lets one request set or clear the due date and the
        # recurrence together: a recurring task must have a due date.
        if command.clear_repeat:
            task.repeat(None, now)
        if command.clear_due_on:
            task.reschedule(None, now)
        elif command.due_on is not None:
            task.reschedule(command.due_on, now)
        if recurrence is not None:
            task.repeat(recurrence, now)
        if command.status is not None:
            task.move_to(command.status, now)
        await self._repository.save(task)
        if not was_done and task.status is TaskStatus.DONE:
            next_task = task.next_occurrence(now)
            if next_task is not None:
                await self._repository.save(next_task)
        return task
