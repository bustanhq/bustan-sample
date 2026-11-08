from bustan import ConfigService, FactoryProvider, Module

from bustan_sample.platform.clock import Clock, ClockModule
from bustan_sample.platform.database import Database, DatabaseModule

from .in_memory_job_queue import InMemoryJobQueue
from .in_memory_schedule_lock import InMemoryScheduleLock
from .job_queue import JobQueue
from .job_scheduler import JobScheduler
from .schedule_lock import ScheduleLock
from .sqlite_job_queue import SqliteJobQueue
from .sqlite_schedule_lock import SqliteScheduleLock


def _job_queue(database: Database, config: ConfigService, clock: Clock) -> JobQueue:
    if database.is_sqlite:
        return SqliteJobQueue(database, config, clock)
    return InMemoryJobQueue(config)


def _schedule_lock(database: Database, clock: Clock) -> ScheduleLock:
    if database.is_sqlite:
        return SqliteScheduleLock(database, clock)
    return InMemoryScheduleLock()


# Each module that enqueues, handles or schedules jobs imports this module.
# All of them get the same queue and the same scheduler. DATABASE_BACKEND
# selects the adapters of JobQueue and ScheduleLock. The factories make only
# the selected adapters, and bustan runs the hooks of those adapters.
@Module(
    imports=[ClockModule, DatabaseModule],
    providers=[
        FactoryProvider(
            provide=JobQueue,
            use_factory=_job_queue,
            inject=(Database, ConfigService, Clock),
        ),
        FactoryProvider(
            provide=ScheduleLock, use_factory=_schedule_lock, inject=(Database, Clock)
        ),
        JobScheduler,
    ],
    exports=[JobQueue, JobScheduler],
)
class JobsModule:
    pass
