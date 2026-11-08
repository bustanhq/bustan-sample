from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
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
