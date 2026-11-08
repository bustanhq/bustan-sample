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
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)
from bustan_sample.platform.clock import FixedClock

PASSWORD = "a long password for the tests"


def _handler() -> tuple[RegisterUserHandler, InMemoryUserRepository]:
    users = InMemoryUserRepository()
    hasher = Argon2PasswordHasher.with_low_cost()
    return RegisterUserHandler(users, hasher, FixedClock()), users


def test_register_stores_the_user_with_a_hash_of_the_password() -> None:
    async def scenario() -> None:
        handler, users = _handler()
        user = await handler.execute(RegisterUserCommand("Ada@Example.com", PASSWORD))
        stored = await users.get_by_email("ada@example.com")
        assert stored == user
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")

    asyncio.run(scenario())


def test_a_second_user_with_the_same_email_is_refused() -> None:
    async def scenario() -> None:
        handler, _ = _handler()
        await handler.execute(RegisterUserCommand("ada@example.com", PASSWORD))
        with pytest.raises(EmailTakenError):
            await handler.execute(RegisterUserCommand("ADA@example.com", PASSWORD))

    asyncio.run(scenario())


def test_a_short_password_is_refused() -> None:
    handler, _ = _handler()
    with pytest.raises(InvalidUserError):
        asyncio.run(handler.execute(RegisterUserCommand("ada@example.com", "short")))
