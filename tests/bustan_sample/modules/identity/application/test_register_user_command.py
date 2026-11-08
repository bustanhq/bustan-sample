import asyncio
from pathlib import Path

import pytest

from bustan_sample.modules.identity.application.register_user_command import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from bustan_sample.modules.identity.domain.errors import (
    EmailTakenError,
    InvalidUserError,
)
from bustan_sample.modules.identity.domain.events import UserRegistered
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)
from bustan_sample.modules.identity.infra.sqlite_user_repository import (
    SqliteUserRepository,
)
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.events import EventBus

from support.database import memory_database, open_sqlite
from support.fakes import RecordingJobQueue, memory_event_bus

PASSWORD = "a long password for the tests"


class _Setup:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.database = memory_database()
        self.events = memory_event_bus(self.database)
        self.published: list[UserRegistered] = []
        self.handler = RegisterUserHandler(
            self.users,
            Argon2PasswordHasher.with_low_cost(),
            FixedClock(),
            self.events,
            self.database,
        )

        async def record(event: UserRegistered) -> None:
            self.published.append(event)

        self.events.subscribe(UserRegistered, record)


def test_register_stores_the_user_and_publishes_user_registered() -> None:
    async def scenario() -> None:
        setup = _Setup()
        user = await setup.handler.execute(RegisterUserCommand("Ada@Example.com", PASSWORD))
        await setup.events.drain(1)
        assert await setup.users.get_by_email("ada@example.com") == user
        assert user.password_hash.startswith("$argon2id$")
        assert setup.published == [UserRegistered(user.id, "ada@example.com", user.created_at)]

    asyncio.run(scenario())


def test_a_second_user_with_the_same_email_is_refused() -> None:
    async def scenario() -> None:
        setup = _Setup()
        await setup.handler.execute(RegisterUserCommand("ada@example.com", PASSWORD))
        with pytest.raises(EmailTakenError):
            await setup.handler.execute(RegisterUserCommand("ADA@example.com", PASSWORD))
        await setup.events.drain(1)
        assert len(setup.published) == 1

    asyncio.run(scenario())


def test_a_short_password_is_refused_and_publishes_nothing() -> None:
    async def scenario() -> None:
        setup = _Setup()
        with pytest.raises(InvalidUserError):
            await setup.handler.execute(RegisterUserCommand("ada@example.com", "short"))
        await setup.events.drain(1)
        assert setup.published == []

    asyncio.run(scenario())


class _BrokenBus(EventBus):
    async def publish(self, event: object) -> None:
        raise ConnectionError("the outbox is not available")


def test_with_sqlite_a_failed_publish_rolls_back_the_user(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "test.db") as database:
            users = SqliteUserRepository(database)
            await users.on_module_init()
            handler = RegisterUserHandler(
                users,
                Argon2PasswordHasher.with_low_cost(),
                FixedClock(),
                _BrokenBus(RecordingJobQueue(), database),
                database,
            )
            with pytest.raises(ConnectionError):
                await handler.execute(RegisterUserCommand("ada@example.com", PASSWORD))
            assert await users.get_by_email("ada@example.com") is None

    asyncio.run(scenario())
