from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ListTasksQuery:
    owner_id: UUID
    status: TaskStatus | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0


@dataclass(frozen=True, slots=True)
class TaskPage:
    """One page of tasks. next_offset is None on the last page."""

    items: list[Task]
    next_offset: int | None


@Injectable()
class ListTasksHandler:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def execute(self, query: ListTasksQuery) -> TaskPage:
        # One task more than the page tells if a next page exists.
        found = await self._repository.find(
            query.owner_id, query.status, query.limit + 1, query.offset
        )
        has_more = len(found) > query.limit
        return TaskPage(
            items=found[: query.limit],
            next_offset=query.offset + query.limit if has_more else None,
        )
