import asyncio
from datetime import timedelta
from uuid import uuid4

from bustan import ConfigService

from bustan_sample.modules.identity.application.authenticate_token_query import (
    AuthenticateTokenHandler,
    AuthenticateTokenQuery,
)
from bustan_sample.modules.identity.domain.user import User
from bustan_sample.modules.identity.infra.in_memory_revoked_token_repository import (
    InMemoryRevokedTokenRepository,
)
from bustan_sample.modules.identity.infra.in_memory_user_repository import (
    InMemoryUserRepository,
)
from bustan_sample.modules.identity.infra.jwt_token_issuer import JwtTokenIssuer
from bustan_sample.platform.clock import FixedClock

SECRET = "a-test-secret-that-is-longer-than-32-characters"


class _Setup:
    def __init__(self) -> None:
        self.clock = FixedClock()
        self.users = InMemoryUserRepository()
        self.revoked = InMemoryRevokedTokenRepository()
        self.issuer = JwtTokenIssuer(ConfigService({"IDENTITY_JWT_SECRET": SECRET}))
        self.handler = AuthenticateTokenHandler(self.issuer, self.revoked, self.users, self.clock)

    async def ada(self) -> User:
        user = User.create("ada@example.com", "hash", self.clock.now())
        await self.users.save(user)
        return user


def test_a_valid_token_gives_the_user_with_the_token_data() -> None:
    async def scenario() -> None:
        setup = _Setup()
        ada = await setup.ada()
        token = setup.issuer.issue(ada.id, setup.clock.now())
        user = await setup.handler.execute(AuthenticateTokenQuery(token.value))
        assert user is not None
        assert (user.user_id, user.roles) == (ada.id, ("user",))
        assert (user.token_id, user.token_expires_at) == (
            token.token_id,
            token.expires_at,
        )

    asyncio.run(scenario())


def test_a_revoked_token_gives_none() -> None:
    async def scenario() -> None:
        setup = _Setup()
        ada = await setup.ada()
        token = setup.issuer.issue(ada.id, setup.clock.now())
        await setup.revoked.revoke(token.token_id, token.expires_at)
        assert await setup.handler.execute(AuthenticateTokenQuery(token.value)) is None

    asyncio.run(scenario())


def test_an_expired_token_or_an_unknown_user_gives_none() -> None:
    async def scenario() -> None:
        setup = _Setup()
        ada = await setup.ada()
        expired = setup.issuer.issue(ada.id, setup.clock.now() - timedelta(hours=1))
        stranger = setup.issuer.issue(uuid4(), setup.clock.now())
        assert await setup.handler.execute(AuthenticateTokenQuery(expired.value)) is None
        assert await setup.handler.execute(AuthenticateTokenQuery(stranger.value)) is None

    asyncio.run(scenario())
