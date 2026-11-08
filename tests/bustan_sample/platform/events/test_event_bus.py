import asyncio
import json
import logging
from dataclasses import dataclass

import pytest

from bustan_sample.platform.events import EventBus


@dataclass(frozen=True)
class Happened:
    value: int


@dataclass(frozen=True)
class Other:
    pass


def test_publish_delivers_to_each_handler_of_the_type() -> None:
    async def scenario() -> None:
        bus, seen = EventBus(), []

        async def first(event: Happened) -> None:
            seen.append(("first", event.value))

        async def second(event: Happened) -> None:
            seen.append(("second", event.value))

        bus.subscribe(Happened, first)
        bus.subscribe(Happened, second)
        await bus.publish(Happened(1))
        await bus.publish(Other())
        assert await bus.drain(1)
        assert sorted(seen) == [("first", 1), ("second", 1)]

    asyncio.run(scenario())


def test_publish_does_not_wait_for_the_handlers() -> None:
    async def scenario() -> None:
        bus, release = EventBus(), asyncio.Event()

        async def slow(event: Happened) -> None:
            await release.wait()

        bus.subscribe(Happened, slow)
        await asyncio.wait_for(bus.publish(Happened(1)), timeout=0.5)
        assert await bus.drain(0.05) is False
        release.set()
        assert await bus.drain(1) is True

    asyncio.run(scenario())


def test_a_failed_handler_is_logged_and_the_others_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> list[int]:
        bus, seen = EventBus(), []

        async def broken(event: Happened) -> None:
            raise RuntimeError("the handler failed on purpose")

        async def working(event: Happened) -> None:
            seen.append(event.value)

        bus.subscribe(Happened, broken)
        bus.subscribe(Happened, working)
        await bus.publish(Happened(7))
        await bus.drain(1)
        return seen

    with caplog.at_level(logging.INFO, logger="bustan"):
        seen = asyncio.run(scenario())
    assert seen == [7]
    records = [
        json.loads(r.getMessage())
        for r in caplog.records
        if "EventBus" in r.getMessage()
    ]
    assert records[0]["message"] == "event handler failed"
    assert records[0]["event"] == "Happened"
    assert records[0]["handler"].endswith("broken")


def test_shutdown_waits_for_the_running_handlers() -> None:
    async def scenario() -> None:
        bus, seen = EventBus(), []

        async def slow(event: Happened) -> None:
            await asyncio.sleep(0.05)
            seen.append(event.value)

        bus.subscribe(Happened, slow)
        await bus.publish(Happened(3))
        await bus.before_application_shutdown(None)
        assert seen == [3]

    asyncio.run(scenario())
