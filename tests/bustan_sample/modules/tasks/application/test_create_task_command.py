import asyncio
from datetime import date
from uuid import uuid4

from bustan_sample.modules.tasks.application.create_task_command import (
    CreateTaskCommand,
    CreateTaskHandler,
)
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.platform.clock import FixedClock


def test_create_stores_a_task_of_the_owner_stamped_with_the_clock() -> None:
    async def scenario() -> None:
        repository, clock, owner = InMemoryTaskRepository(), FixedClock(), uuid4()
        handler = CreateTaskHandler(repository, clock)
        task = await handler.execute(
            CreateTaskCommand(owner_id=owner, title="a", due_on=date(2026, 2, 1))
        )
        assert task.owner_id == owner
        assert task.created_at == clock.now()
        assert await repository.get(owner, task.id) == task

    asyncio.run(scenario())
