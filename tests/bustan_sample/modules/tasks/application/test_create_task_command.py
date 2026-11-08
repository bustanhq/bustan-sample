import asyncio
from datetime import date
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.application.create_task_command import (
    CreateTaskCommand,
    CreateTaskHandler,
)
from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
from bustan_sample.modules.tasks.domain.recurrence import Frequency, RecurrenceRule
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.modules.tasks.infra.rule_based_recurrence_parser import (
    RuleBasedRecurrenceParser,
)
from bustan_sample.platform.clock import FixedClock


def _handler() -> tuple[CreateTaskHandler, InMemoryTaskRepository, FixedClock]:
    repository, clock = InMemoryTaskRepository(), FixedClock()
    return (
        CreateTaskHandler(repository, clock, RuleBasedRecurrenceParser()),
        repository,
        clock,
    )


def test_create_stores_a_task_of_the_owner_stamped_with_the_clock() -> None:
    async def scenario() -> None:
        handler, repository, clock = _handler()
        owner = uuid4()
        task = await handler.execute(
            CreateTaskCommand(owner_id=owner, title="a", due_on=date(2026, 2, 1))
        )
        assert task.owner_id == owner
        assert task.created_at == clock.now()
        assert task.recurrence is None
        assert await repository.get(owner, task.id) == task

    asyncio.run(scenario())


def test_a_repeat_phrase_becomes_the_rule_of_the_task() -> None:
    async def scenario() -> None:
        handler, *_ = _handler()
        task = await handler.execute(
            CreateTaskCommand(
                owner_id=uuid4(),
                title="water the plants",
                due_on=date(2026, 2, 2),
                repeat="every 2 weeks on Monday",
            )
        )
        assert task.recurrence == RecurrenceRule(Frequency.WEEKLY, 2, weekday=0)

    asyncio.run(scenario())


def test_an_unknown_phrase_or_no_due_date_is_refused() -> None:
    async def scenario() -> None:
        handler, *_ = _handler()
        with pytest.raises(InvalidTaskError):
            await handler.execute(
                CreateTaskCommand(
                    uuid4(), "a", due_on=date(2026, 2, 2), repeat="sometimes"
                )
            )
        with pytest.raises(InvalidTaskError):
            await handler.execute(CreateTaskCommand(uuid4(), "a", repeat="weekly"))

    asyncio.run(scenario())
