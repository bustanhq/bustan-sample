import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)


def test_a_saved_user_is_found_by_id_and_by_email() -> None:
    async def scenario() -> None:
        repository = InMemoryUserRepository()
        user = User.create("ada@example.com", "hash", datetime(2026, 1, 1, tzinfo=UTC))
        await repository.save(user)
        assert await repository.get(user.id) == user
        assert await repository.get_by_email("ada@example.com") == user
        assert await repository.get(uuid4()) is None
        assert await repository.get_by_email("bob@example.com") is None

    asyncio.run(scenario())
