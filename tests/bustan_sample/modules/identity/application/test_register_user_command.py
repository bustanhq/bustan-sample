import asyncio

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
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.events import EventBus

PASSWORD = "a long password for the tests"


class _Setup:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.events = EventBus()
        self.published: list[UserRegistered] = []
        self.handler = RegisterUserHandler(
            self.users, Argon2PasswordHasher.with_low_cost(), FixedClock(), self.events
        )

        async def record(event: UserRegistered) -> None:
            self.published.append(event)

        self.events.subscribe(UserRegistered, record)


def test_register_stores_the_user_and_publishes_user_registered() -> None:
    async def scenario() -> None:
        setup = _Setup()
        user = await setup.handler.execute(
            RegisterUserCommand("Ada@Example.com", PASSWORD)
        )
        await setup.events.drain(1)
        assert await setup.users.get_by_email("ada@example.com") == user
        assert user.password_hash.startswith("$argon2id$")
        assert setup.published == [
            UserRegistered(user.id, "ada@example.com", user.created_at)
        ]

    asyncio.run(scenario())


def test_a_second_user_with_the_same_email_is_refused() -> None:
    async def scenario() -> None:
        setup = _Setup()
        await setup.handler.execute(RegisterUserCommand("ada@example.com", PASSWORD))
        with pytest.raises(EmailTakenError):
            await setup.handler.execute(
                RegisterUserCommand("ADA@example.com", PASSWORD)
            )
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
