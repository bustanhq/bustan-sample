from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.errors import TaskNotFoundError
from ..domain.task import Task
from ..domain.task_repository import TaskRepository


@dataclass(frozen=True, slots=True)
class GetTaskQuery:
    owner_id: UUID
    task_id: UUID


@Injectable()
class GetTaskHandler:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def execute(self, query: GetTaskQuery) -> Task:
        task = await self._repository.get(query.owner_id, query.task_id)
        if task is None:
            raise TaskNotFoundError(query.task_id)
        return task
