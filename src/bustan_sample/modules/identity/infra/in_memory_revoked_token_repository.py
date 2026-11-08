from datetime import datetime

from bustan import Injectable

from ..domain.revoked_token_repository import RevokedTokenRepository


@Injectable()
class InMemoryRevokedTokenRepository(RevokedTokenRepository):
    """Keeps the revoked token ids in a dict, with the expiry time of each token.

    The data goes when the process stops, and each process has its own data.
    Thus a deployment with more than one process needs a shared store, for
    example Redis, behind the same port.
    """

    def __init__(self) -> None:
        self._revoked: dict[str, datetime] = {}

    async def revoke(self, token_id: str, expires_at: datetime, now: datetime) -> None:
        self._revoked = {
            key: expiry for key, expiry in self._revoked.items() if expiry > now
        }
        self._revoked[token_id] = expires_at

    async def is_revoked(self, token_id: str) -> bool:
        return token_id in self._revoked
