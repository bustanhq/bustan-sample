"""The contract of the RevokedTokenRepository port. Each test runs on each adapter."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from bustan_sample.modules.identity.domain.revoked_token_repository import (
    RevokedTokenRepository,
)
from bustan_sample.modules.identity.infra.in_memory_revoked_token_repository import (
    InMemoryRevokedTokenRepository,
)
from bustan_sample.modules.identity.infra.sqlite_revoked_token_repository import (
    SqliteRevokedTokenRepository,
)

from support.database import BACKENDS, open_sqlite

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

pytestmark = pytest.mark.parametrize("backend", BACKENDS)


@asynccontextmanager
async def _repository(backend: str, path: Path) -> AsyncGenerator[RevokedTokenRepository]:
    if backend == "memory":
        yield InMemoryRevokedTokenRepository()
        return
    async with open_sqlite(path) as database:
        repository = SqliteRevokedTokenRepository(database)
        await repository.on_module_init()
        yield repository


def test_a_revoked_token_id_is_found(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            await repository.revoke("a", T0 + timedelta(minutes=15))
            assert await repository.is_revoked("a") is True
            assert await repository.is_revoked("b") is False

    asyncio.run(scenario())


def test_purge_removes_only_the_entries_of_expired_tokens(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            await repository.revoke("old", T0 + timedelta(minutes=1))
            await repository.revoke("new", T0 + timedelta(minutes=30))
            assert await repository.purge(T0 + timedelta(minutes=5)) == 1
            assert await repository.is_revoked("old") is False
            assert await repository.is_revoked("new") is True

    asyncio.run(scenario())
