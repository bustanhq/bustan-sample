from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from .errors import InvalidUserError

EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


@dataclass(slots=True)
class User:
    """A person who can log in. The entity keeps only the hash of the password."""

    id: UUID
    email: str
    password_hash: str
    created_at: datetime

    @classmethod
    def create(cls, email: str, password_hash: str, now: datetime) -> Self:
        return cls(
            id=uuid4(),
            email=normalize_email(email),
            password_hash=password_hash,
            created_at=now,
        )


def normalize_email(email: str) -> str:
    """Return the email address in lower case, or raise InvalidUserError."""
    email = email.strip().lower()
    local, at, domain = email.partition("@")
    if (
        not at
        or not local
        or "." not in domain.strip(".")
        or " " in email
        or len(email) > EMAIL_MAX_LENGTH
    ):
        raise InvalidUserError("the email address is not valid")
    return email


def check_password_policy(password: str) -> None:
    """Raise InvalidUserError if the password does not obey the policy."""
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise InvalidUserError(
            f"the password must have {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters"
        )
