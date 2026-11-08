import asyncio
from datetime import UTC, datetime, timedelta

from bustan_sample.modules.identity.infra.in_memory_revoked_token_repository import (
    InMemoryRevokedTokenRepository,
)

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def test_a_revoked_token_id_is_found() -> None:
    async def scenario() -> None:
        repository = InMemoryRevokedTokenRepository()
        await repository.revoke("a", T0 + timedelta(minutes=15))
        assert await repository.is_revoked("a") is True
        assert await repository.is_revoked("b") is False

    asyncio.run(scenario())


def test_purge_removes_only_the_entries_of_expired_tokens() -> None:
    async def scenario() -> None:
        repository = InMemoryRevokedTokenRepository()
        await repository.revoke("old", T0 + timedelta(minutes=1))
        await repository.revoke("new", T0 + timedelta(minutes=30))
        assert await repository.purge(T0 + timedelta(minutes=5)) == 1
        assert await repository.is_revoked("old") is False
        assert await repository.is_revoked("new") is True

    asyncio.run(scenario())
