from dataclasses import dataclass
from datetime import datetime

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.revoked_token_repository import RevokedTokenRepository


@dataclass(frozen=True, slots=True)
class LogOutCommand:
    token_id: str
    token_expires_at: datetime


@Injectable()
class LogOutHandler:
    """Revokes the access token of the request before it expires."""

    def __init__(self, revoked: RevokedTokenRepository, clock: Clock) -> None:
        self._revoked = revoked
        self._clock = clock

    async def execute(self, command: LogOutCommand) -> None:
        await self._revoked.revoke(
            command.token_id, command.token_expires_at, self._clock.now()
        )
