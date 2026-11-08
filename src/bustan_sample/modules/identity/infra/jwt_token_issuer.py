from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from bustan import ConfigService, Injectable

from ..domain.token_issuer import AccessToken, TokenClaims, TokenIssuer

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["iss", "sub", "jti", "iat", "exp"]


@Injectable()
class JwtTokenIssuer(TokenIssuer):
    """Signs access tokens as JWTs with HS256 and the secret from the settings."""

    def __init__(self, config: ConfigService) -> None:
        self._secret = str(config.get_or_throw("IDENTITY_JWT_SECRET"))
        self._issuer = str(config.get("IDENTITY_JWT_ISSUER", "bustan-sample"))
        self._ttl = timedelta(minutes=int(config.get("IDENTITY_TOKEN_TTL_MINUTES", 15)))

    def issue(self, user_id: UUID, now: datetime) -> AccessToken:
        token_id = uuid4().hex
        expires_at = int((now + self._ttl).timestamp())
        claims = {
            "iss": self._issuer,
            "sub": str(user_id),
            "jti": token_id,
            "iat": int(now.timestamp()),
            "exp": expires_at,
        }
        value = jwt.encode(claims, self._secret, algorithm=ALGORITHM)
        return AccessToken(
            value=value,
            token_id=token_id,
            expires_at=datetime.fromtimestamp(expires_at, UTC),
        )

    def read(self, token: str, now: datetime) -> TokenClaims | None:
        try:
            # The algorithm list stops a token that names a different algorithm.
            # PyJWT does not examine the times, because the injected clock is
            # the authority for the time. The check of "exp" is below.
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                issuer=self._issuer,
                options={
                    "require": REQUIRED_CLAIMS,
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
            user_id = UUID(str(claims["sub"]))
            expires_at = datetime.fromtimestamp(int(claims["exp"]), UTC)
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return None
        if expires_at <= now:
            return None
        return TokenClaims(user_id=user_id, token_id=str(claims["jti"]), expires_at=expires_at)
