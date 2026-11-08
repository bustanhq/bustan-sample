import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bustan_sample.modules.identity.application.get_current_user_query import (
    GetCurrentUserHandler,
    GetCurrentUserQuery,
)
from bustan_sample.modules.identity.domain.errors import UserNotFoundError
from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)


def test_the_stored_user_is_returned() -> None:
    async def scenario() -> None:
        users = InMemoryUserRepository()
        ada = User.create("ada@example.com", "hash", datetime(2026, 1, 1, tzinfo=UTC))
        await users.save(ada)
        assert await GetCurrentUserHandler(users).execute(GetCurrentUserQuery(ada.id)) == ada

    asyncio.run(scenario())


def test_an_unknown_user_raises_not_found() -> None:
    handler = GetCurrentUserHandler(InMemoryUserRepository())
    with pytest.raises(UserNotFoundError):
        asyncio.run(handler.execute(GetCurrentUserQuery(uuid4())))
