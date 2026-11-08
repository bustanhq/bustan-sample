import asyncio
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from bustan_sample.modules.tasks.domain.task import Task
from bustan_sample.modules.tasks.infra.sqlite_task_repository import (
    SqliteTaskRepository,
)

from support.database import open_sqlite

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def test_a_task_is_still_there_after_the_database_opens_again(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, owner = tmp_path / "test.db", uuid4()
        task = Task.create(owner, "keep me", "", date(2026, 2, 2), T0)
        async with open_sqlite(path) as database:
            repository = SqliteTaskRepository(database)
            await repository.on_module_init()
            await repository.save(task)
        async with open_sqlite(path) as database:
            repository = SqliteTaskRepository(database)
            await repository.on_module_init()
            assert await repository.get(owner, task.id) == task

    asyncio.run(scenario())
