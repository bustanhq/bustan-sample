import asyncio
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.application.get_task_query import (
    GetTaskHandler,
    GetTaskQuery,
)
from bustan_sample.modules.tasks.domain.errors import TaskNotFoundError
from bustan_sample.modules.tasks.domain.task import Task
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.platform.clock import FixedClock

ADA, BOB = uuid4(), uuid4()


def test_get_returns_the_task_of_the_owner() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, FixedClock().now())
        await repository.save(task)
        assert await GetTaskHandler(repository).execute(GetTaskQuery(ADA, task.id)) == task

    asyncio.run(scenario())


def test_a_task_of_another_owner_raises_not_found() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, FixedClock().now())
        await repository.save(task)
        with pytest.raises(TaskNotFoundError):
            await GetTaskHandler(repository).execute(GetTaskQuery(BOB, task.id))

    asyncio.run(scenario())
