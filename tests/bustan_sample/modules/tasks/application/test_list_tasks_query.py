import asyncio
from uuid import uuid4

from bustan_sample.modules.tasks.application.list_tasks_query import (
    ListTasksHandler,
    ListTasksQuery,
)
from bustan_sample.modules.tasks.domain.task import Task, TaskStatus
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.platform.clock import FixedClock

ADA, BOB = uuid4(), uuid4()


def test_list_gives_the_tasks_of_the_owner_filtered_on_status() -> None:
    async def scenario() -> None:
        repository, clock = InMemoryTaskRepository(), FixedClock()
        open_task = Task.create(ADA, "open", "", None, clock.now())
        done_task = Task.create(ADA, "done", "", None, clock.advance())
        done_task.move_to(TaskStatus.DONE, clock.now())
        other = Task.create(BOB, "other", "", None, clock.advance())
        for task in (open_task, done_task, other):
            await repository.save(task)
        handler = ListTasksHandler(repository)
        everything = await handler.execute(ListTasksQuery(ADA))
        done = await handler.execute(ListTasksQuery(ADA, status=TaskStatus.DONE))
        assert [task.title for task in everything] == ["open", "done"]
        assert [task.title for task in done] == ["done"]

    asyncio.run(scenario())
