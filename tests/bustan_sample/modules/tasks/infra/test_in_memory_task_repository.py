import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from bustan_sample.modules.tasks.domain.task import Task, TaskStatus
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
ADA, BOB = uuid4(), uuid4()


def test_a_change_has_no_effect_until_save() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, T0)
        await repository.save(task)
        task.rename("b", T0)
        stored = await repository.get(ADA, task.id)
        assert stored is not None and stored.title == "a"
        await repository.save(task)
        stored = await repository.get(ADA, task.id)
        assert stored is not None and stored.title == "b"

    asyncio.run(scenario())


def test_find_keeps_the_creation_sequence_and_filters_on_status() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        later = Task.create(ADA, "later", "", None, T0 + timedelta(minutes=1))
        earlier = Task.create(ADA, "earlier", "", None, T0)
        later.move_to(TaskStatus.DONE, T0 + timedelta(minutes=2))
        await repository.save(later)
        await repository.save(earlier)
        assert [task.title for task in await repository.find(ADA)] == [
            "earlier",
            "later",
        ]
        done = await repository.find(ADA, TaskStatus.DONE)
        assert [task.title for task in done] == ["later"]

    asyncio.run(scenario())


def test_an_owner_sees_and_removes_only_own_tasks() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "private", "", None, T0)
        await repository.save(task)
        assert await repository.get(BOB, task.id) is None
        assert await repository.find(BOB) == []
        assert await repository.remove(BOB, task.id) is False
        assert await repository.get(ADA, task.id) is not None

    asyncio.run(scenario())


def test_remove_tells_if_the_task_was_there() -> None:
    async def scenario() -> None:
        repository = InMemoryTaskRepository()
        task = Task.create(ADA, "a", "", None, T0)
        await repository.save(task)
        assert await repository.remove(ADA, task.id) is True
        assert await repository.remove(ADA, task.id) is False
        assert await repository.get(ADA, uuid4()) is None

    asyncio.run(scenario())
