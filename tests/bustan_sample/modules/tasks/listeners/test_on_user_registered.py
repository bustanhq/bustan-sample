import asyncio
from uuid import uuid4

from bustan_sample.modules.identity import UserRegistered
from bustan_sample.modules.tasks.application.create_task_command import (
    CreateTaskHandler,
)
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.modules.tasks.infra.rule_based_recurrence_parser import (
    RuleBasedRecurrenceParser,
)
from bustan_sample.modules.tasks.listeners.on_user_registered import (
    STARTER_TITLE,
    OnUserRegistered,
)
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.events import EventBus


def test_a_new_user_gets_a_starter_task() -> None:
    async def scenario() -> None:
        events, repository, clock = EventBus(), InMemoryTaskRepository(), FixedClock()
        create_task = CreateTaskHandler(repository, clock, RuleBasedRecurrenceParser())
        OnUserRegistered(events, create_task).on_module_init()
        user_id = uuid4()
        await events.publish(UserRegistered(user_id, "ada@example.com", clock.now()))
        await events.drain(1)
        [task] = await repository.find(user_id)
        assert task.title == STARTER_TITLE

    asyncio.run(scenario())
