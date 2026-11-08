from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
from bustan_sample.modules.tasks.domain.recurrence import Frequency, RecurrenceRule
from bustan_sample.modules.tasks.domain.task import TITLE_MAX_LENGTH, Task, TaskStatus

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
T1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
OWNER = uuid4()


def test_a_new_task_is_todo_with_a_stripped_title() -> None:
    task = Task.create(OWNER, "  write the skill  ", "", date(2026, 2, 1), T0)
    assert task.owner_id == OWNER
    assert task.title == "write the skill"
    assert task.status is TaskStatus.TODO
    assert task.created_at == task.updated_at == T0


@pytest.mark.parametrize("title", ["", "   ", "x" * (TITLE_MAX_LENGTH + 1)])
def test_an_invalid_title_is_refused(title: str) -> None:
    with pytest.raises(InvalidTaskError):
        Task.create(OWNER, title, "", None, T0)


def test_each_change_sets_updated_at() -> None:
    task = Task.create(OWNER, "a", "", None, T0)
    task.move_to(TaskStatus.DONE, T1)
    assert task.status is TaskStatus.DONE
    assert task.updated_at == T1
    assert task.created_at == T0


def test_rename_obeys_the_title_rules() -> None:
    task = Task.create(OWNER, "a", "", None, T0)
    with pytest.raises(InvalidTaskError):
        task.rename(" ", T1)
    assert task.title == "a"


WEEKLY = RecurrenceRule(Frequency.WEEKLY)


def test_a_recurring_task_must_have_a_due_date() -> None:
    with pytest.raises(InvalidTaskError):
        Task.create(OWNER, "a", "", None, T0, WEEKLY)
    task = Task.create(OWNER, "a", "", date(2026, 2, 2), T0, WEEKLY)
    with pytest.raises(InvalidTaskError):
        task.reschedule(None, T1)
    plain = Task.create(OWNER, "b", "", None, T0)
    with pytest.raises(InvalidTaskError):
        plain.repeat(WEEKLY, T1)


def test_the_next_occurrence_is_a_new_todo_task_on_the_next_due_date() -> None:
    task = Task.create(OWNER, "report", "notes", date(2026, 2, 2), T0, WEEKLY)
    task.move_to(TaskStatus.DONE, T1)
    following = task.next_occurrence(T1)
    assert following is not None
    assert following.id != task.id
    assert (following.owner_id, following.title, following.description) == (
        OWNER,
        "report",
        "notes",
    )
    assert (following.status, following.due_on) == (TaskStatus.TODO, date(2026, 2, 9))
    assert following.recurrence == WEEKLY
    assert following.created_at == T1


def test_a_task_that_does_not_recur_has_no_next_occurrence() -> None:
    assert Task.create(OWNER, "a", "", date(2026, 2, 2), T0).next_occurrence(T1) is None
