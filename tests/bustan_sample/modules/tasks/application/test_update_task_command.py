import asyncio
from datetime import date
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.application.update_task_command import (
    UpdateTaskCommand,
    UpdateTaskHandler,
)
from bustan_sample.modules.tasks.domain.errors import TaskNotFoundError
from bustan_sample.modules.tasks.domain.task import Task, TaskStatus
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.platform.clock import FixedClock

ADA, BOB = uuid4(), uuid4()


def test_update_changes_only_the_given_fields() -> None:
    async def scenario() -> None:
        repository, clock = InMemoryTaskRepository(), FixedClock()
        task = Task.create(ADA, "keep", "notes", date(2026, 2, 1), clock.now())
        await repository.save(task)
        clock.advance()
        handler = UpdateTaskHandler(repository, clock)
        updated = await handler.execute(
            UpdateTaskCommand(ADA, task.id, status=TaskStatus.DONE)
        )
        assert (updated.title, updated.description, updated.due_on) == (
            "keep",
            "notes",
            date(2026, 2, 1),
        )
        assert updated.status is TaskStatus.DONE
        assert updated.updated_at == clock.now() != updated.created_at
        assert await repository.get(ADA, task.id) == updated

    asyncio.run(scenario())


def test_clear_due_on_removes_the_due_date() -> None:
    async def scenario() -> None:
        repository, clock = InMemoryTaskRepository(), FixedClock()
        task = Task.create(ADA, "a", "", date(2026, 2, 1), clock.now())
        await repository.save(task)
        handler = UpdateTaskHandler(repository, clock)
        updated = await handler.execute(
            UpdateTaskCommand(ADA, task.id, clear_due_on=True)
        )
        assert updated.due_on is None

    asyncio.run(scenario())


def test_a_task_of_another_owner_raises_not_found() -> None:
    async def scenario() -> None:
        repository, clock = InMemoryTaskRepository(), FixedClock()
        task = Task.create(ADA, "a", "", None, clock.now())
        await repository.save(task)
        handler = UpdateTaskHandler(repository, clock)
        with pytest.raises(TaskNotFoundError):
            await handler.execute(UpdateTaskCommand(BOB, task.id, title="taken"))
        stored = await repository.get(ADA, task.id)
        assert stored is not None and stored.title == "a"

    asyncio.run(scenario())
