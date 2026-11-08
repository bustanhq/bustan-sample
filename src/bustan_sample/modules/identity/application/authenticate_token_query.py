from dataclasses import dataclass

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.authenticated_user import AuthenticatedUser
from ..domain.revoked_token_repository import RevokedTokenRepository
from ..domain.token_issuer import TokenIssuer
from ..domain.user_repository import UserRepository

USER_ROLE = "user"


@dataclass(frozen=True, slots=True)
class AuthenticateTokenQuery:
    token: str


@Injectable()
class AuthenticateTokenHandler:
    """Returns the user of a valid access token, or None.

    A token is valid if the signature is correct, the token did not expire,
    the logout did not revoke it, and the user exists.
    """

    def __init__(
        self,
        issuer: TokenIssuer,
        revoked: RevokedTokenRepository,
        users: UserRepository,
        clock: Clock,
    ) -> None:
        self._issuer = issuer
        self._revoked = revoked
        self._users = users
        self._clock = clock

    async def execute(self, query: AuthenticateTokenQuery) -> AuthenticatedUser | None:
        claims = self._issuer.read(query.token, self._clock.now())
        if claims is None or await self._revoked.is_revoked(claims.token_id):
            return None
        if await self._users.get(claims.user_id) is None:
            return None
        return AuthenticatedUser(
            id=str(claims.user_id),
            roles=(USER_ROLE,),
            permissions=(),
            token_id=claims.token_id,
            token_expires_at=claims.expires_at,
        )
