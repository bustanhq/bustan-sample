import asyncio
from typing import Self

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError
from bustan import Injectable

from ..domain.password_hasher import PasswordHasher


@Injectable()
class Argon2PasswordHasher(PasswordHasher):
    """Hashes passwords with Argon2id and the default parameters of argon2-cffi.

    A hash takes tens of milliseconds of CPU time. The work runs on a worker
    thread, thus it does not stop the event loop.
    """

    def __init__(self) -> None:
        self._argon2 = Argon2()
        self._dummy_hash: str | None = None

    @classmethod
    def with_low_cost(cls) -> Self:
        """Return a fast hasher for tests. Do not use it in production."""
        hasher = cls()
        hasher._argon2 = Argon2(time_cost=1, memory_cost=1024, parallelism=1)
        return hasher

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._argon2.hash, password)

    async def verify(self, password_hash: str | None, password: str) -> bool:
        return await asyncio.to_thread(self._verify, password_hash, password)

    def _verify(self, password_hash: str | None, password: str) -> bool:
        if password_hash is None:
            self._check(self._dummy(), password)
            return False
        return self._check(password_hash, password)

    def _check(self, password_hash: str, password: str) -> bool:
        try:
            return self._argon2.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def _dummy(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = self._argon2.hash("a password that no user has")
        return self._dummy_hash
