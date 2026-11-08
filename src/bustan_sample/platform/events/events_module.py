from bustan import Module

from .event_bus import EventBus


# Each module that publishes or handles events imports this module. All of
# them get the same EventBus instance.
@Module(providers=[EventBus], exports=[EventBus])
class EventsModule:
    pass
