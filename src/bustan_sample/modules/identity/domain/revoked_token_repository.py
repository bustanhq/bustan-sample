from abc import ABC, abstractmethod
from datetime import datetime


class RevokedTokenRepository(ABC):
    """The storage port for the ids of revoked tokens.

    A signed token stays valid until it expires. The logout puts the token id
    in this store, and the authentication refuses each token id in it. An entry
    is necessary only until the token expires. A scheduled job removes the
    entries of expired tokens.
    """

    @abstractmethod
    async def revoke(self, token_id: str, expires_at: datetime) -> None:
        """Add the token id, with the time at which the token expires."""

    @abstractmethod
    async def is_revoked(self, token_id: str) -> bool:
        """Return True if the token id is in the store."""

    @abstractmethod
    async def purge(self, now: datetime) -> int:
        """Remove the entries of the tokens that expired before now. Return the count."""
