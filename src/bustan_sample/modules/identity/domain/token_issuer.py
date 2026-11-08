from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessToken:
    """A signed access token and the data that the logout needs to revoke it."""

    value: str
    token_id: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """The claims of an access token with a correct signature that did not expire."""

    user_id: UUID
    token_id: str
    expires_at: datetime


class TokenIssuer(ABC):
    """The port that signs access tokens and reads them again."""

    @abstractmethod
    def issue(self, user_id: UUID, now: datetime) -> AccessToken:
        """Return a new signed token for the user, with a unique token id."""

    @abstractmethod
    def read(self, token: str, now: datetime) -> TokenClaims | None:
        """Return the claims, or None if the token is not valid at the time now."""
