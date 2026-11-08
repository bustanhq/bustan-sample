from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.errors import UserNotFoundError
from ..domain.user import User
from ..domain.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class GetCurrentUserQuery:
    user_id: UUID


@Injectable()
class GetCurrentUserHandler:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, query: GetCurrentUserQuery) -> User:
        user = await self._users.get(query.user_id)
        if user is None:
            raise UserNotFoundError(query.user_id)
        return user
