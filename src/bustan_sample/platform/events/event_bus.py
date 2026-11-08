import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from bustan import Injectable, Logger, LogLevel
from pydantic import TypeAdapter

from bustan_sample.platform.database import Database
from bustan_sample.platform.jobs import JobQueue

type EventHandler[E] = Callable[[E], Awaitable[None]]

SHUTDOWN_TIMEOUT_SECONDS = 10.0
DELIVERY_ATTEMPTS = 5


@dataclass(frozen=True, slots=True)
class DeliverEvent:
    """The job that gives one event to one handler, with the SQLite backend."""

    event_type: str
    handler: str
    payload: str


@Injectable()
class EventBus:
    """Delivers each event to the handlers of its type.

    With the memory backend, publish() starts one asyncio task for each
    handler and returns immediately. A handler error goes to the log. The bus
    keeps no events. At shutdown it waits for the running handlers for
    SHUTDOWN_TIMEOUT_SECONDS, then it cancels the remaining handlers.

    With the SQLite backend, publish() enqueues one DeliverEvent job for each
    handler in the durable job queue. Thus a delivery survives a restart, and
    a handler that fails runs again, until DELIVERY_ATTEMPTS attempts. A
    handler can run more than one time for one event, thus it must give the
    same result each time. The publisher saves its data first and publishes
    after: if the process stops between the two, the event is lost.

    An event is a dataclass that pydantic can write as JSON. The job keeps the
    class name of the event and the module and the name of the handler. Thus
    a rename of a handler leaves its queued deliveries with no handler.
    """

    def __init__(self, jobs: JobQueue, database: Database) -> None:
        self._jobs = jobs
        self.durable = database.is_sqlite
        self._handlers: defaultdict[type, list[tuple[str, EventHandler[object]]]] = defaultdict(
            list
        )
        self._by_name: dict[tuple[str, str], tuple[type, EventHandler[object]]] = {}
        self._running: set[asyncio.Task[None]] = set()
        self._logger = Logger("EventBus")

    def on_module_init(self) -> None:
        # The bus is a dependency of each listener, thus this hook runs before
        # the hooks in which the listeners subscribe.
        if self.durable:
            self._jobs.register(DeliverEvent, self._run_delivery, max_attempts=DELIVERY_ATTEMPTS)

    def subscribe[E](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Call handler for each event of exactly this type."""
        name = _name(handler)
        key = (event_type.__name__, name)
        if key in self._by_name:
            raise ValueError(f"{name} is subscribed to {event_type.__name__}")
        entry = cast(EventHandler[object], handler)
        self._handlers[event_type].append((name, entry))
        self._by_name[key] = (event_type, entry)

    async def publish(self, event: object) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return
        if self.durable:
            event_type = type(event)
            payload = TypeAdapter(event_type).dump_json(event).decode()
            for name, _ in handlers:
                await self._jobs.enqueue(DeliverEvent(event_type.__name__, name, payload))
            return
        for name, handler in handlers:
            task = asyncio.create_task(self._deliver(name, handler, event))
            self._running.add(task)
            task.add_done_callback(self._running.discard)

    async def drain(self, timeout: float | None = None) -> bool:
        """Wait for the running handlers of the memory backend, and for the ones they start.

        Return False if the timeout ends first. With the SQLite backend, use the
        drain() of the job queue.
        """
        try:
            async with asyncio.timeout(timeout):
                while self._running:
                    await asyncio.wait(set(self._running))
        except TimeoutError:
            return False
        return True

    async def before_application_shutdown(self, signal: str | None) -> None:
        if await self.drain(SHUTDOWN_TIMEOUT_SECONDS):
            return
        self._logger.record(
            LogLevel.WARN,
            "event handlers cancelled at shutdown",
            fields={"count": len(self._running)},
        )
        for task in self._running:
            task.cancel()

    async def _deliver(self, name: str, handler: EventHandler[object], event: object) -> None:
        try:
            await handler(event)
        # Any error of a handler stops here, thus it cannot stop other handlers.
        except Exception as exc:  # noqa: BLE001
            self._log_failure(type(event).__name__, name, exc)

    async def _run_delivery(self, job: DeliverEvent) -> None:
        entry = self._by_name.get((job.event_type, job.handler))
        if entry is None:
            raise LookupError(f"no handler {job.handler} for {job.event_type}")
        event_type, handler = entry
        try:
            await handler(TypeAdapter(event_type).validate_json(job.payload))
        except Exception as exc:
            self._log_failure(job.event_type, job.handler, exc)
            raise

    def _log_failure(self, event: str, handler: str, exc: Exception) -> None:
        self._logger.record(
            LogLevel.ERROR,
            "event handler failed",
            fields={"event": event, "handler": handler, "error": repr(exc)},
        )


def _name(handler: object) -> str:
    module = getattr(handler, "__module__", "")
    qualname = getattr(handler, "__qualname__", repr(handler))
    return f"{module}.{qualname}" if module else qualname
