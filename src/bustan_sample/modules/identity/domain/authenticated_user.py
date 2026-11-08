from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The user behind one request, after the access token passed all checks.

    The attributes id, roles and permissions agree with the Principal protocol
    of bustan, thus the framework accepts this class with no import of bustan.
    The token attributes let the logout revoke the token of the request.
    """

    id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    token_id: str
    token_expires_at: datetime

    @property
    def user_id(self) -> UUID:
        return UUID(self.id)
