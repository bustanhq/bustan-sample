from abc import ABC, abstractmethod
from uuid import UUID

from .task import Task, TaskStatus


class TaskRepository(ABC):
    """The storage port of the tasks module.

    The application layer depends on this class only. The infra layer gives the
    implementation, and the module binds the two. The methods are async, thus a
    database adapter can replace the adapter in memory with no change here.

    Each read and each removal takes the owner id. Thus no caller can get a
    task of a different user, and a task of a different user looks the same as
    a task that does not exist.
    """

    @abstractmethod
    async def save(self, task: Task) -> None:
        """Add the task, or replace the stored task that has the same id."""

    @abstractmethod
    async def get(self, owner_id: UUID, task_id: UUID) -> Task | None:
        """Return the task of this owner, or None."""

    @abstractmethod
    async def find(
        self, owner_id: UUID, status: TaskStatus | None = None
    ) -> list[Task]:
        """Return the tasks of this owner in the sequence of creation.

        If status is given, return only the tasks with that status.
        """

    @abstractmethod
    async def remove(self, owner_id: UUID, task_id: UUID) -> bool:
        """Remove the task of this owner. Return False if it does not exist."""
