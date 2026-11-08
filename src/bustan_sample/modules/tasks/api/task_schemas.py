from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from ..domain.task import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH, Task, TaskStatus

Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH),
]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=DESCRIPTION_MAX_LENGTH)
]


class CreateTaskRequest(BaseModel):
    """The JSON body of POST /tasks."""

    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description = ""
    due_on: date | None = None


class UpdateTaskRequest(BaseModel):
    """The JSON body of PATCH /tasks/{task_id}.

    A field that the client does not send does not change. A due_on of null
    removes the due date.
    """

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    status: TaskStatus | None = None
    due_on: date | None = None


class TaskResponse(BaseModel):
    """The JSON shape of a task in each response."""

    id: UUID
    title: str
    description: str
    status: TaskStatus
    due_on: date | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: Task) -> Self:
        return cls.model_validate(task, from_attributes=True)

    def to_json(self) -> dict[str, object]:
        return self.model_dump(mode="json")
