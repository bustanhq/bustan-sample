from abc import ABC, abstractmethod
from datetime import datetime


class RevokedTokenRepository(ABC):
    """The storage port for the ids of revoked tokens.

    A signed token stays valid until it expires. The logout puts the token id
    in this store, and the authentication refuses each token id in it. An entry
    is necessary only until the token expires.
    """

    @abstractmethod
    async def revoke(self, token_id: str, expires_at: datetime, now: datetime) -> None:
        """Add the token id. An adapter can remove entries that expired before now."""

    @abstractmethod
    async def is_revoked(self, token_id: str) -> bool:
        """Return True if the token id is in the store."""
