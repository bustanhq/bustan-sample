from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.errors import TaskNotFoundError
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class DeleteTaskCommand:
    owner_id: UUID
    task_id: UUID


@Injectable()
class DeleteTaskHandler:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def execute(self, command: DeleteTaskCommand) -> None:
        if not await self._repository.remove(command.owner_id, command.task_id):
            raise TaskNotFoundError(command.task_id)
