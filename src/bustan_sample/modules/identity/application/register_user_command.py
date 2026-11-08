from dataclasses import dataclass

from bustan import Injectable

from bustan_sample.platform.clock import Clock
from bustan_sample.platform.events import EventBus

from ..domain.errors import EmailTakenError
from ..domain.events import UserRegistered
from ..domain.password_hasher import PasswordHasher
from ..domain.user import User, check_password_policy, normalize_email
from ..domain.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str


@Injectable()
class RegisterUserHandler:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        clock: Clock,
        events: EventBus,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._clock = clock
        self._events = events

    async def execute(self, command: RegisterUserCommand) -> User:
        email = normalize_email(command.email)
        check_password_policy(command.password)
        if await self._users.get_by_email(email) is not None:
            raise EmailTakenError()
        password_hash = await self._hasher.hash(command.password)
        user = User.create(email, password_hash, self._clock.now())
        await self._users.save(user)
        # The event goes out after the save, thus a handler can read the user.
        await self._events.publish(UserRegistered(user.id, user.email, user.created_at))
        return user
