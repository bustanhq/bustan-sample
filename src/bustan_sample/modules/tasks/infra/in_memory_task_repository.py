from dataclasses import replace
from uuid import UUID

from bustan import Injectable

from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository


@Injectable()
class InMemoryTaskRepository(TaskRepository):
    """Keeps the tasks in a dict. The data goes when the process stops.

    The repository stores and returns copies. Thus a change to a task has no
    effect on the store until a handler calls save().
    """

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    async def save(self, task: Task) -> None:
        self._tasks[task.id] = replace(task)

    async def get(self, owner_id: UUID, task_id: UUID) -> Task | None:
        stored = self._tasks.get(task_id)
        if stored is None or stored.owner_id != owner_id:
            return None
        return replace(stored)

    async def find(
        self,
        owner_id: UUID,
        status: TaskStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        tasks = sorted(self._tasks.values(), key=lambda task: task.created_at)
        found = [
            replace(task)
            for task in tasks
            if task.owner_id == owner_id and (status is None or task.status is status)
        ]
        end = None if limit is None else offset + limit
        return found[offset:end]

    async def remove(self, owner_id: UUID, task_id: UUID) -> bool:
        if await self.get(owner_id, task_id) is None:
            return False
        del self._tasks[task_id]
        return True
