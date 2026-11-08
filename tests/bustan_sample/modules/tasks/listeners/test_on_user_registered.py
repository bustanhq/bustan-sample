import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from bustan_sample.modules.identity import UserRegistered
from bustan_sample.modules.tasks.application.create_task_command import (
    CreateTaskHandler,
)
from bustan_sample.modules.tasks.domain.task_repository import TaskRepository
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.modules.tasks.infra.rule_based_recurrence_parser import (
    RuleBasedRecurrenceParser,
)
from bustan_sample.modules.tasks.infra.sqlite_task_repository import (
    SqliteTaskRepository,
)
from bustan_sample.modules.tasks.listeners.on_user_registered import (
    STARTER_TITLE,
    OnUserRegistered,
)
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.database import Database
from bustan_sample.platform.idempotency import (
    IdempotencyKeys,
    InMemoryIdempotencyKeys,
    SqliteIdempotencyKeys,
)

from support.database import BACKENDS, memory_database, open_sqlite
from support.fakes import memory_event_bus

CLOCK = FixedClock()


@asynccontextmanager
async def _stores(
    backend: str, path: Path
) -> AsyncGenerator[tuple[Database, TaskRepository, IdempotencyKeys]]:
    if backend == "memory":
        database = memory_database()
        yield database, InMemoryTaskRepository(), InMemoryIdempotencyKeys(database)
        return
    async with open_sqlite(path) as database:
        repository, keys = SqliteTaskRepository(database), SqliteIdempotencyKeys(database, CLOCK)
        await repository.on_module_init()
        await keys.on_module_init()
        yield database, repository, keys


def _listener(
    database: Database, repository: TaskRepository, keys: IdempotencyKeys
) -> OnUserRegistered:
    create_task = CreateTaskHandler(repository, CLOCK, RuleBasedRecurrenceParser())
    return OnUserRegistered(memory_event_bus(database), create_task, database, keys)


def test_a_new_user_gets_a_starter_task() -> None:
    async def scenario() -> None:
        database = memory_database()
        events, repository = memory_event_bus(database), InMemoryTaskRepository()
        create_task = CreateTaskHandler(repository, CLOCK, RuleBasedRecurrenceParser())
        keys = InMemoryIdempotencyKeys(database)
        OnUserRegistered(events, create_task, database, keys).on_module_init()
        user_id = uuid4()
        await events.publish(UserRegistered(user_id, "ada@example.com", CLOCK.now()))
        await events.drain(1)
        [task] = await repository.find(user_id)
        assert task.title == STARTER_TITLE

    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_two_deliveries_of_one_event_give_one_starter_task(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _stores(backend, tmp_path / "test.db") as (database, repository, keys):
            listener = _listener(database, repository, keys)
            event = UserRegistered(uuid4(), "ada@example.com", CLOCK.now())
            await listener.handle(event)
            await listener.handle(event)
            assert len(await repository.find(event.user_id)) == 1

    asyncio.run(scenario())
