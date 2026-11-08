import asyncio
from datetime import timedelta

from bustan_sample.modules.identity.application.log_out_command import (
    LogOutCommand,
    LogOutHandler,
)
from bustan_sample.modules.identity.infra.in_memory_revoked_token_repository import (
    InMemoryRevokedTokenRepository,
)
from bustan_sample.platform.clock import FixedClock


def test_log_out_revokes_the_token_id() -> None:
    async def scenario() -> None:
        revoked = InMemoryRevokedTokenRepository()
        expires_at = FixedClock().now() + timedelta(minutes=15)
        await LogOutHandler(revoked).execute(LogOutCommand("token-1", expires_at))
        assert await revoked.is_revoked("token-1") is True

    asyncio.run(scenario())
