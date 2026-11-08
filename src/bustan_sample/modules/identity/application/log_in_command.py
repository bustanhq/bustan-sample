from dataclasses import dataclass

from bustan import Injectable

from bustan_sample.platform.clock import Clock

from ..domain.errors import InvalidCredentialsError, InvalidUserError
from ..domain.password_hasher import PasswordHasher
from ..domain.token_issuer import AccessToken, TokenIssuer
from ..domain.user import normalize_email
from ..domain.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class LogInCommand:
    email: str
    password: str


@Injectable()
class LogInHandler:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        issuer: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._issuer = issuer
        self._clock = clock

    async def execute(self, command: LogInCommand) -> AccessToken:
        # Each failure gives the same error, and the hasher does the same work
        # for an unknown email address. Thus a caller cannot find which email
        # addresses have an account.
        try:
            user = await self._users.get_by_email(normalize_email(command.email))
        except InvalidUserError:
            user = None
        password_hash = None if user is None else user.password_hash
        if (
            not await self._hasher.verify(password_hash, command.password)
            or user is None
        ):
            raise InvalidCredentialsError()
        return self._issuer.issue(user.id, self._clock.now())
