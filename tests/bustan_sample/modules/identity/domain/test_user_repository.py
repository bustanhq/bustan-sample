"""The contract of the UserRepository port. Each test runs on each adapter."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from support.database import BACKENDS, open_sqlite

from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.domain.user_repository import UserRepository
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)
from bustan_sample.modules.identity.infra.sqlite_user_repository import (
    SqliteUserRepository,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)

pytestmark = pytest.mark.parametrize("backend", BACKENDS)


@asynccontextmanager
async def _repository(backend: str, path: Path) -> AsyncGenerator[UserRepository]:
    if backend == "memory":
        yield InMemoryUserRepository()
        return
    async with open_sqlite(path) as database:
        repository = SqliteUserRepository(database)
        await repository.on_module_init()
        yield repository


def test_a_saved_user_is_found_by_id_and_by_email(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            user = User.create("ada@example.com", "hash", T0)
            await repository.save(user)
            assert await repository.get(user.id) == user
            assert await repository.get_by_email("ada@example.com") == user
            assert await repository.get(uuid4()) is None
            assert await repository.get_by_email("bob@example.com") is None

    asyncio.run(scenario())


def test_a_second_save_replaces_the_user(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            user = User.create("ada@example.com", "old hash", T0)
            await repository.save(user)
            user.password_hash = "new hash"
            await repository.save(user)
            stored = await repository.get(user.id)
            assert stored is not None and stored.password_hash == "new hash"

    asyncio.run(scenario())
