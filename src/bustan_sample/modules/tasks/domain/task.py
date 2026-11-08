from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from .errors import InvalidTaskError

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(slots=True)
class Task:
    """A unit of work that belongs to one user.

    The entity keeps its own rules. It knows nothing about HTTP, about storage
    or about the framework. Each change sets updated_at to the time it gets.
    owner_id is the id of a user of the identity module. The tasks domain
    keeps only the id and does not import the identity module.
    """

    id: UUID
    owner_id: UUID
    title: str
    description: str
    status: TaskStatus
    due_on: date | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        owner_id: UUID,
        title: str,
        description: str,
        due_on: date | None,
        now: datetime,
    ) -> Self:
        return cls(
            id=uuid4(),
            owner_id=owner_id,
            title=_valid_title(title),
            description=_valid_description(description),
            status=TaskStatus.TODO,
            due_on=due_on,
            created_at=now,
            updated_at=now,
        )

    def rename(self, title: str, now: datetime) -> None:
        self.title = _valid_title(title)
        self.updated_at = now

    def describe(self, description: str, now: datetime) -> None:
        self.description = _valid_description(description)
        self.updated_at = now

    def reschedule(self, due_on: date | None, now: datetime) -> None:
        self.due_on = due_on
        self.updated_at = now

    def move_to(self, status: TaskStatus, now: datetime) -> None:
        self.status = status
        self.updated_at = now


def _valid_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise InvalidTaskError("the title must contain text")
    if len(title) > TITLE_MAX_LENGTH:
        raise InvalidTaskError(
            f"the title must not be longer than {TITLE_MAX_LENGTH} characters"
        )
    return title


def _valid_description(description: str) -> str:
    description = description.strip()
    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise InvalidTaskError(
            f"the description must not be longer than {DESCRIPTION_MAX_LENGTH} characters"
        )
    return description
