from bustan import Module

from bustan_sample.platform.database import DatabaseModule
from bustan_sample.platform.jobs import JobsModule

from .event_bus import EventBus


# Each module that publishes or handles events imports this module. All of
# them get the same EventBus instance. With the SQLite backend, the bus gives
# each delivery to the durable job queue.
@Module(imports=[DatabaseModule, JobsModule], providers=[EventBus], exports=[EventBus])
class EventsModule:
    pass
