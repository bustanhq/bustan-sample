from dataclasses import dataclass
from datetime import date
from uuid import UUID

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.task import Task
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    owner_id: UUID
    title: str
    description: str = ""
    due_on: date | None = None


@Injectable()
class CreateTaskHandler:
    def __init__(self, repository: TaskRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: CreateTaskCommand) -> Task:
        task = Task.create(
            command.owner_id,
            command.title,
            command.description,
            command.due_on,
            self._clock.now(),
        )
        await self._repository.save(task)
        return task
