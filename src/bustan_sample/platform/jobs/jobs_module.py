from bustan import ClassProvider, Module

from bustan_sample.platform.clock import ClockModule

from .in_memory_job_queue import InMemoryJobQueue
from .job_queue import JobQueue
from .job_scheduler import JobScheduler


# Each module that enqueues, handles or schedules jobs imports this module.
# All of them get the same queue and the same scheduler. To use a durable
# store, bind JobQueue to a different adapter here.
@Module(
    imports=[ClockModule],
    providers=[
        ClassProvider(provide=JobQueue, use_class=InMemoryJobQueue),
        JobScheduler,
    ],
    exports=[JobQueue, JobScheduler],
)
class JobsModule:
    pass
