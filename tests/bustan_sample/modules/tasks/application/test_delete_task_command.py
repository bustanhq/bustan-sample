import asyncio
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.application.delete_task_command import (
    DeleteTaskCommand,
    DeleteTaskHandler,
)
from bustan_sample.modules.tasks.domain.errors import TaskNotFoundError
from bustan_sample.modules.tasks.domain.task import Task
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.platform.clock import FixedClock

ADA, BOB = uuid4(), uuid4()


def test_delete_removes_the_task() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, FixedClock().now())
        await repository.save(task)
        await DeleteTaskHandler(repository).execute(DeleteTaskCommand(ADA, task.id))
        assert await repository.get(ADA, task.id) is None

    asyncio.run(scenario())


def test_a_task_of_another_owner_raises_not_found() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, FixedClock().now())
        await repository.save(task)
        with pytest.raises(TaskNotFoundError):
            await DeleteTaskHandler(repository).execute(DeleteTaskCommand(BOB, task.id))
        assert await repository.get(ADA, task.id) is not None

    asyncio.run(scenario())
