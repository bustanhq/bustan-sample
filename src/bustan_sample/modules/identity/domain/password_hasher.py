from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """The port for password hashes. The methods are async because a hash is slow."""

    @abstractmethod
    async def hash(self, password: str) -> str:
        """Return a salted hash of the password."""

    @abstractmethod
    async def verify(self, password_hash: str | None, password: str) -> bool:
        """Return True if the password agrees with the hash.

        If password_hash is None (no user has the email address), do the same
        work and return False. Thus the response time does not show if a user
        exists.
        """
