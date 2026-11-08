from abc import ABC, abstractmethod
from uuid import UUID

from .user import User


class UserRepository(ABC):
    """The storage port for users."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Add the user, or replace the stored user that has the same id."""

    @abstractmethod
    async def get(self, user_id: UUID) -> User | None:
        """Return the user, or None if no user has the id."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this normalized email address, or None."""
