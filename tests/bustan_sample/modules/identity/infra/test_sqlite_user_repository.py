import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from support.database import open_sqlite

from bustan_sample.modules.identity.domain.errors import EmailTakenError
from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.infra.sqlite_user_repository import (
    SqliteUserRepository,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_a_second_user_with_the_same_email_raises_email_taken(tmp_path: Path) -> None:
    # The unique column stops two registrations that pass the check of the
    # handler at the same time.
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "test.db") as database:
            repository = SqliteUserRepository(database)
            await repository.on_module_init()
            await repository.save(User.create("ada@example.com", "hash", T0))
            with pytest.raises(EmailTakenError):
                await repository.save(User.create("ada@example.com", "hash", T0))

    asyncio.run(scenario())
