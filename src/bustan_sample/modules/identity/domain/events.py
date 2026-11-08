from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserRegistered:
    """A user registered. Other modules can handle this event."""

    user_id: UUID
    email: str
    occurred_at: datetime
