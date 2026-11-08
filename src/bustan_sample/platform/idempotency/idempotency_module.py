from bustan import FactoryProvider, Module

from bustan_sample.platform.clock import Clock, ClockModule
from bustan_sample.platform.database import Database, DatabaseModule

from .idempotency_keys import IdempotencyKeys
from .in_memory_idempotency_keys import InMemoryIdempotencyKeys
from .sqlite_idempotency_keys import SqliteIdempotencyKeys


def _idempotency_keys(database: Database, clock: Clock) -> IdempotencyKeys:
    if database.is_sqlite:
        return SqliteIdempotencyKeys(database, clock)
    return InMemoryIdempotencyKeys(database)


# Each module with work that must happen one time imports this module. All of
# them get the same store. DATABASE_BACKEND selects the adapter.
@Module(
    imports=[ClockModule, DatabaseModule],
    providers=[
        FactoryProvider(
            provide=IdempotencyKeys,
            use_factory=_idempotency_keys,
            inject=(Database, Clock),
        ),
    ],
    exports=[IdempotencyKeys],
)
class IdempotencyModule:
    pass
