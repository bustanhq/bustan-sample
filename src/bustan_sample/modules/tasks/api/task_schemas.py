from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ..domain.task import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH, Task, TaskStatus

REPEAT_MAX_LENGTH = 100

Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH),
]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=DESCRIPTION_MAX_LENGTH)
]
Repeat = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=REPEAT_MAX_LENGTH
    ),
    Field(
        description='A repeat phrase, for example "weekly" or "every 2 weeks on Monday".'
        " A recurring task must have a due date.",
        examples=["every 2 weeks on Monday"],
    ),
]


class CreateTaskRequest(BaseModel):
    """The JSON body of POST /tasks."""

    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description = ""
    due_on: date | None = None
    repeat: Repeat | None = None


class UpdateTaskRequest(BaseModel):
    """The JSON body of PATCH /tasks/{task_id}.

    A field that the client does not send does not change. A due_on of null
    removes the due date. A repeat of null stops the recurrence.
    """

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    status: TaskStatus | None = None
    due_on: date | None = None
    repeat: Repeat | None = None


class TaskResponse(BaseModel):
    """The JSON shape of a task in each response.

    repeat is the rule of a recurring task as a phrase, in the same form for
    each phrase that gives the same rule.
    """

    id: UUID
    title: str
    description: str
    status: TaskStatus
    due_on: date | None
    repeat: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: Task) -> Self:
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            due_on=task.due_on,
            repeat=None if task.recurrence is None else task.recurrence.describe(),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def to_json(self) -> dict[str, object]:
        return self.model_dump(mode="json")
