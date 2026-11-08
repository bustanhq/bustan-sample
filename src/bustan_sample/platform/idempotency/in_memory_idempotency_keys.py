from bustan import Injectable

from bustan_sample.platform.database import Database

from .idempotency_keys import IdempotencyKeys


@Injectable()
class InMemoryIdempotencyKeys(IdempotencyKeys):
    """Keeps the keys in a set of this process.

    The memory backend has no rollback. Thus, if the transaction of an add()
    rolls back, the adapter removes the key again. The keys are lost if the
    process stops.
    """

    def __init__(self, database: Database) -> None:
        self._database = database
        self._keys: set[str] = set()

    async def add(self, key: str) -> bool:
        if key in self._keys:
            return False
        self._keys.add(key)
        self._database.after_rollback(lambda: self._keys.discard(key))
        return True

    async def contains(self, key: str) -> bool:
        return key in self._keys
