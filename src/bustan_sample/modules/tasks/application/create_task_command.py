from dataclasses import dataclass
from datetime import date
from uuid import UUID

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.recurrence_parser import RecurrenceParser
from ..domain.task import Task
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    owner_id: UUID
    title: str
    description: str = ""
    due_on: date | None = None
    repeat: str | None = None


@Injectable()
class CreateTaskHandler:
    def __init__(self, repository: TaskRepository, clock: Clock, parser: RecurrenceParser) -> None:
        self._repository = repository
        self._clock = clock
        self._parser = parser

    async def execute(self, command: CreateTaskCommand) -> Task:
        recurrence = None if command.repeat is None else await self._parser.parse(command.repeat)
        task = Task.create(
            command.owner_id,
            command.title,
            command.description,
            command.due_on,
            self._clock.now(),
            recurrence,
        )
        await self._repository.save(task)
        return task
