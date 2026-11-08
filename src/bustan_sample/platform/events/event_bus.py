import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import cast

from bustan import Injectable, Logger, LogLevel

type EventHandler[E] = Callable[[E], Awaitable[None]]

SHUTDOWN_TIMEOUT_SECONDS = 10.0


@Injectable()
class EventBus:
    """Delivers each event to its handlers in background tasks, in this process.

    publish() starts one task for each handler of the type of the event, and
    returns immediately. A handler error goes to the log and has no effect on
    the publisher or on the other handlers. Work that must not be lost, or that
    needs retries, goes from the handler to the job queue.

    The bus keeps no events. At shutdown it waits for the running handlers for
    SHUTDOWN_TIMEOUT_SECONDS, then it cancels the remaining handlers.
    """

    def __init__(self) -> None:
        self._handlers: defaultdict[type, list[EventHandler[object]]] = defaultdict(
            list
        )
        self._running: set[asyncio.Task[None]] = set()
        self._logger = Logger("EventBus")

    def subscribe[E](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Call handler for each event of exactly this type."""
        self._handlers[event_type].append(cast(EventHandler[object], handler))

    async def publish(self, event: object) -> None:
        for handler in self._handlers.get(type(event), ()):
            task = asyncio.create_task(self._deliver(handler, event))
            self._running.add(task)
            task.add_done_callback(self._running.discard)

    async def drain(self, timeout: float | None = None) -> bool:
        """Wait for the running handlers, and for the handlers that they start.

        Return False if the timeout ends first.
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

    async def _deliver(self, handler: EventHandler[object], event: object) -> None:
        try:
            await handler(event)
        # Any error of a handler stops here, thus it cannot stop other handlers.
        except Exception as exc:  # noqa: BLE001
            self._logger.record(
                LogLevel.ERROR,
                "event handler failed",
                fields={
                    "event": type(event).__name__,
                    "handler": _name(handler),
                    "error": repr(exc),
                },
            )


def _name(handler: object) -> str:
    module = getattr(handler, "__module__", "")
    qualname = getattr(handler, "__qualname__", repr(handler))
    return f"{module}.{qualname}" if module else qualname
