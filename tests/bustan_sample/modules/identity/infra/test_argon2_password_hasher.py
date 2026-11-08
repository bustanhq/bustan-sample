import asyncio

from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)


def test_a_hash_is_argon2id_and_verifies_only_the_same_password() -> None:
    async def scenario() -> None:
        hasher = Argon2PasswordHasher.with_low_cost()
        password_hash = await hasher.hash("a long password")
        assert password_hash.startswith("$argon2id$")
        assert await hasher.verify(password_hash, "a long password") is True
        assert await hasher.verify(password_hash, "a different password") is False

    asyncio.run(scenario())


def test_no_hash_or_a_damaged_hash_gives_false() -> None:
    async def scenario() -> None:
        hasher = Argon2PasswordHasher.with_low_cost()
        assert await hasher.verify(None, "a long password") is False
        assert await hasher.verify("not a hash", "a long password") is False

    asyncio.run(scenario())
