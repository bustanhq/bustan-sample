import asyncio

import pytest
from bustan import ConfigService

from bustan_sample.modules.identity.application.log_in_command import (
    LogInCommand,
    LogInHandler,
)
from bustan_sample.modules.identity.domain.errors import InvalidCredentialsError
from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)
from bustan_sample.modules.identity.infra.jwt_token_issuer import JwtTokenIssuer
from bustan_sample.platform.clock import FixedClock

PASSWORD = "a long password for the tests"
SECRET = "a-test-secret-that-is-longer-than-32-characters"


async def _handler_with_ada() -> tuple[LogInHandler, JwtTokenIssuer, User, FixedClock]:
    users, hasher, clock = (
        InMemoryUserRepository(),
        Argon2PasswordHasher.with_low_cost(),
        FixedClock(),
    )
    issuer = JwtTokenIssuer(ConfigService({"IDENTITY_JWT_SECRET": SECRET}))
    ada = User.create("ada@example.com", await hasher.hash(PASSWORD), clock.now())
    await users.save(ada)
    return LogInHandler(users, hasher, issuer, clock), issuer, ada, clock


def test_correct_credentials_give_a_token_for_the_user() -> None:
    async def scenario() -> None:
        handler, issuer, ada, clock = await _handler_with_ada()
        token = await handler.execute(LogInCommand(" ADA@example.com", PASSWORD))
        claims = issuer.read(token.value, clock.now())
        assert claims is not None and claims.user_id == ada.id

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ada@example.com", "an incorrect password"),
        ("bob@example.com", PASSWORD),
        ("not an email", PASSWORD),
    ],
)
def test_each_bad_credential_gives_the_same_error(email: str, password: str) -> None:
    async def scenario() -> None:
        handler, *_ = await _handler_with_ada()
        with pytest.raises(InvalidCredentialsError):
            await handler.execute(LogInCommand(email, password))

    asyncio.run(scenario())
