from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class ListTasksQuery:
    owner_id: UUID
    status: TaskStatus | None = None


@Injectable()
class ListTasksHandler:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def execute(self, query: ListTasksQuery) -> list[Task]:
        return await self._repository.find(query.owner_id, query.status)
