from dataclasses import replace
from uuid import UUID

from bustan import Injectable

from ..domain.user import User
from ..domain.user_repository import UserRepository


@Injectable()
class InMemoryUserRepository(UserRepository):
    """Keeps the users in a dict. The data goes when the process stops."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def save(self, user: User) -> None:
        self._users[user.id] = replace(user)

    async def get(self, user_id: UUID) -> User | None:
        stored = self._users.get(user_id)
        return None if stored is None else replace(stored)

    async def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return replace(user)
        return None
