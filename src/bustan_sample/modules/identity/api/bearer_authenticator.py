from bustan import ExecutionContext, Injectable

from ..application.authenticate_token_query import (
    AuthenticateTokenHandler,
    AuthenticateTokenQuery,
)
from ..domain.authenticated_user import AuthenticatedUser

STRATEGY = "bearer"


@Injectable()
class BearerAuthenticator:
    """The bustan authenticator for the strategy "bearer".

    It reads the token from the Authorization header. It returns the user, or
    None. The framework changes None into a 401 response.
    """

    def __init__(self, authenticate: AuthenticateTokenHandler) -> None:
        self._authenticate = authenticate

    async def authenticate(self, context: ExecutionContext) -> AuthenticatedUser | None:
        request = context.request
        header = "" if request is None else request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            return None
        return await self._authenticate.execute(AuthenticateTokenQuery(token=token))
