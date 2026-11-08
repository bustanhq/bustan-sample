import asyncio
from datetime import date
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.application.update_task_command import (
    UpdateTaskCommand,
    UpdateTaskHandler,
)
from bustan_sample.modules.tasks.domain.errors import (
    InvalidTaskError,
    TaskNotFoundError,
)
from bustan_sample.modules.tasks.domain.recurrence import Frequency, RecurrenceRule
from bustan_sample.modules.tasks.domain.task import Task, TaskStatus
from bustan_sample.modules.tasks.infra.in_memory_task_repository import (
    InMemoryTaskRepository,
)
from bustan_sample.modules.tasks.infra.rule_based_recurrence_parser import (
    RuleBasedRecurrenceParser,
)
from bustan_sample.platform.clock import FixedClock

ADA, BOB = uuid4(), uuid4()
WEEKLY = RecurrenceRule(Frequency.WEEKLY)


class _Setup:
    def __init__(self) -> None:
        self.repository = InMemoryTaskRepository()
        self.clock = FixedClock()
        self.handler = UpdateTaskHandler(self.repository, self.clock, RuleBasedRecurrenceParser())

    async def add(self, task: Task) -> Task:
        await self.repository.save(task)
        return task


def test_update_changes_only_the_given_fields() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(
            Task.create(ADA, "keep", "notes", date(2026, 2, 1), setup.clock.now())
        )
        setup.clock.advance()
        updated = await setup.handler.execute(
            UpdateTaskCommand(ADA, task.id, status=TaskStatus.DONE)
        )
        assert (updated.title, updated.description, updated.due_on) == (
            "keep",
            "notes",
            date(2026, 2, 1),
        )
        assert updated.status is TaskStatus.DONE
        assert updated.updated_at == setup.clock.now() != updated.created_at
        assert await setup.repository.get(ADA, task.id) == updated

    asyncio.run(scenario())


def test_clear_due_on_removes_the_due_date() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(Task.create(ADA, "a", "", date(2026, 2, 1), setup.clock.now()))
        updated = await setup.handler.execute(UpdateTaskCommand(ADA, task.id, clear_due_on=True))
        assert updated.due_on is None

    asyncio.run(scenario())


def test_a_task_of_another_owner_raises_not_found() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(Task.create(ADA, "a", "", None, setup.clock.now()))
        with pytest.raises(TaskNotFoundError):
            await setup.handler.execute(UpdateTaskCommand(BOB, task.id, title="taken"))
        stored = await setup.repository.get(ADA, task.id)
        assert stored is not None and stored.title == "a"

    asyncio.run(scenario())


def test_a_done_recurring_task_adds_the_next_task_once() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(
            Task.create(ADA, "report", "", date(2026, 2, 2), setup.clock.now(), WEEKLY)
        )
        done = UpdateTaskCommand(ADA, task.id, status=TaskStatus.DONE)
        await setup.handler.execute(done)
        await setup.handler.execute(done)
        tasks = await setup.repository.find(ADA)
        assert [(t.status, t.due_on) for t in tasks] == [
            (TaskStatus.DONE, date(2026, 2, 2)),
            (TaskStatus.TODO, date(2026, 2, 9)),
        ]
        assert tasks[1].recurrence == WEEKLY

    asyncio.run(scenario())


def test_one_request_can_set_the_due_date_and_the_repeat_together() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(Task.create(ADA, "a", "", None, setup.clock.now()))
        updated = await setup.handler.execute(
            UpdateTaskCommand(ADA, task.id, due_on=date(2026, 3, 1), repeat="monthly")
        )
        assert updated.recurrence == RecurrenceRule(Frequency.MONTHLY)
        cleared = await setup.handler.execute(
            UpdateTaskCommand(ADA, task.id, clear_repeat=True, clear_due_on=True)
        )
        assert (cleared.recurrence, cleared.due_on) == (None, None)

    asyncio.run(scenario())


def test_removing_the_due_date_of_a_recurring_task_is_refused() -> None:
    async def scenario() -> None:
        setup = _Setup()
        task = await setup.add(
            Task.create(ADA, "a", "", date(2026, 2, 2), setup.clock.now(), WEEKLY)
        )
        with pytest.raises(InvalidTaskError):
            await setup.handler.execute(UpdateTaskCommand(ADA, task.id, clear_due_on=True))

    asyncio.run(scenario())
