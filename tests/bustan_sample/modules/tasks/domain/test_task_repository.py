"""The contract of the TaskRepository port. Each test runs on each adapter."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from support.database import BACKENDS, open_sqlite

from bustan_sample.modules.tasks.domain.recurrence import Frequency, RecurrenceRule
from bustan_sample.modules.tasks.domain.task import Task, TaskStatus
from bustan_sample.modules.tasks.domain.task_repository import TaskRepository
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.modules.tasks.infra.sqlite_task_repository import (
    SqliteTaskRepository,
)

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
ADA, BOB = uuid4(), uuid4()

pytestmark = pytest.mark.parametrize("backend", BACKENDS)


@asynccontextmanager
async def _repository(backend: str, path: Path) -> AsyncGenerator[TaskRepository]:
    if backend == "memory":
        yield InMemoryTaskRepository()
        return
    async with open_sqlite(path) as database:
        repository = SqliteTaskRepository(database)
        await repository.on_module_init()
        yield repository


def test_a_change_has_no_effect_until_save(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            task = Task.create(ADA, "a", "", None, T0)
            await repository.save(task)
            task.rename("b", T0)
            stored = await repository.get(ADA, task.id)
            assert stored is not None and stored.title == "a"
            await repository.save(task)
            assert await repository.get(ADA, task.id) == task

    asyncio.run(scenario())


def test_all_fields_and_the_recurrence_read_back(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            rule = RecurrenceRule(Frequency.WEEKLY, 2, weekday=0)
            task = Task.create(ADA, "report", "notes", date(2026, 2, 2), T0, rule)
            task.move_to(TaskStatus.IN_PROGRESS, T0 + timedelta(seconds=1.5))
            await repository.save(task)
            assert await repository.get(ADA, task.id) == task

    asyncio.run(scenario())


def test_find_keeps_the_creation_sequence_and_filters_on_status(
    backend: str, tmp_path: Path
) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            later = Task.create(ADA, "later", "", None, T0 + timedelta(minutes=1))
            earlier = Task.create(ADA, "earlier", "", None, T0)
            later.move_to(TaskStatus.DONE, T0 + timedelta(minutes=2))
            await repository.save(later)
            await repository.save(earlier)
            assert [t.title for t in await repository.find(ADA)] == ["earlier", "later"]
            done = await repository.find(ADA, TaskStatus.DONE)
            assert [t.title for t in done] == ["later"]

    asyncio.run(scenario())


def test_tasks_with_the_same_time_keep_the_save_sequence(
    backend: str, tmp_path: Path
) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            for title in ("first", "second", "third"):
                await repository.save(Task.create(ADA, title, "", None, T0))
            titles = [t.title for t in await repository.find(ADA)]
            assert titles == ["first", "second", "third"]

    asyncio.run(scenario())


def test_an_owner_sees_and_removes_only_own_tasks(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            task = Task.create(ADA, "private", "", None, T0)
            await repository.save(task)
            assert await repository.get(BOB, task.id) is None
            assert await repository.find(BOB) == []
            assert await repository.remove(BOB, task.id) is False
            assert await repository.get(ADA, task.id) is not None

    asyncio.run(scenario())


def test_remove_tells_if_the_task_was_there(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            task = Task.create(ADA, "a", "", None, T0)
            await repository.save(task)
            assert await repository.remove(ADA, task.id) is True
            assert await repository.remove(ADA, task.id) is False
            assert await repository.get(ADA, uuid4()) is None

    asyncio.run(scenario())
