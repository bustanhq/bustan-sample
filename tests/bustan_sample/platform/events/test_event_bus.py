import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.database import Database
from bustan_sample.platform.events import EventBus
from bustan_sample.platform.jobs import SqliteJobQueue

from support.database import memory_database, open_sqlite, sqlite_config
from support.fakes import memory_event_bus


@dataclass(frozen=True)
class Happened:
    value: int


@dataclass(frozen=True)
class Other:
    pass


def test_publish_delivers_to_each_handler_of_the_type() -> None:
    async def scenario() -> None:
        bus, seen = memory_event_bus(), []

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
        bus, release = memory_event_bus(), asyncio.Event()

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
        bus, seen = memory_event_bus(), []

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
    records = [json.loads(r.getMessage()) for r in caplog.records if "EventBus" in r.getMessage()]
    assert records[0]["message"] == "event handler failed"
    assert records[0]["event"] == "Happened"
    assert records[0]["handler"].endswith("broken")


def test_shutdown_waits_for_the_running_handlers() -> None:
    async def scenario() -> None:
        bus, seen = memory_event_bus(), []

        async def slow(event: Happened) -> None:
            await asyncio.sleep(0.05)
            seen.append(event.value)

        bus.subscribe(Happened, slow)
        await bus.publish(Happened(3))
        await bus.before_application_shutdown(None)
        assert seen == [3]

    asyncio.run(scenario())


def _durable(database: Database, path: Path) -> tuple[EventBus, SqliteJobQueue]:
    config = sqlite_config(path, JOBS_RETRY_DELAY_SECONDS=0, JOBS_POLL_SECONDS=0.01)
    queue = SqliteJobQueue(database, config, FixedClock())
    return EventBus(queue, database), queue


@dataclass(frozen=True)
class Registered:
    user_id: UUID
    at: datetime


def test_a_durable_delivery_goes_through_the_job_queue(tmp_path: Path) -> None:
    async def scenario() -> list[Registered]:
        path, seen = tmp_path / "test.db", []

        async def handle(event: Registered) -> None:
            seen.append(event)

        async with open_sqlite(path) as database:
            bus, queue = _durable(database, path)
            await queue.on_module_init()
            bus.on_module_init()
            bus.subscribe(Registered, handle)
            await queue.on_application_bootstrap()
            event = Registered(uuid4(), datetime(2026, 1, 1, tzinfo=UTC))
            await bus.publish(event)
            assert await queue.drain(2)
            await queue.on_application_shutdown(None)
        assert seen == [event]
        return seen

    asyncio.run(scenario())


def test_a_durable_delivery_survives_a_restart_and_retries(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, attempts = tmp_path / "test.db", []

        async def flaky(event: Registered) -> None:
            attempts.append(event.user_id)
            if len(attempts) < 2:
                raise ConnectionError("not yet")

        event = Registered(uuid4(), datetime(2026, 1, 1, tzinfo=UTC))
        async with open_sqlite(path) as database:
            bus, queue = _durable(database, path)
            await queue.on_module_init()
            bus.on_module_init()
            bus.subscribe(Registered, flaky)
            await bus.publish(event)  # no worker runs before the restart
        async with open_sqlite(path) as database:
            bus, queue = _durable(database, path)
            await queue.on_module_init()
            bus.on_module_init()
            bus.subscribe(Registered, flaky)
            await queue.on_application_bootstrap()
            assert await queue.drain(2)
            await queue.on_application_shutdown(None)
        assert attempts == [event.user_id, event.user_id]

    asyncio.run(scenario())


def test_a_publish_in_a_transaction_delivers_after_the_commit() -> None:
    async def scenario() -> None:
        database, seen = memory_database(), []
        bus = memory_event_bus(database)

        async def handle(event: Happened) -> None:
            seen.append(event.value)

        bus.subscribe(Happened, handle)
        async with database.transaction():
            await bus.publish(Happened(1))
            await asyncio.sleep(0.01)
            assert seen == []
        assert await bus.drain(1)
        assert seen == [1]

    asyncio.run(scenario())


def test_a_rollback_drops_the_events_of_the_transaction() -> None:
    async def scenario() -> None:
        database, seen = memory_database(), []
        bus = memory_event_bus(database)

        async def handle(event: Happened) -> None:
            seen.append(event.value)

        bus.subscribe(Happened, handle)
        with pytest.raises(ValueError):
            async with database.transaction():
                await bus.publish(Happened(1))
                raise ValueError("the save failed")
        assert await bus.drain(1)
        assert seen == []

    asyncio.run(scenario())


def test_the_outbox_rows_commit_or_roll_back_with_the_data(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, seen = tmp_path / "test.db", []

        async def handle(event: Registered) -> None:
            seen.append(event)

        async with open_sqlite(path) as database:
            bus, queue = _durable(database, path)
            await queue.on_module_init()
            bus.on_module_init()
            bus.subscribe(Registered, handle)
            await database.execute_script("CREATE TABLE users (id TEXT)")
            lost = Registered(uuid4(), datetime(2026, 1, 1, tzinfo=UTC))
            with pytest.raises(ValueError):
                async with database.transaction():
                    await database.execute("INSERT INTO users VALUES (?)", (str(lost.user_id),))
                    await bus.publish(lost)
                    raise ValueError("stop after the publish")
            assert await database.fetch_all("SELECT id FROM users") == []
            assert await database.fetch_all("SELECT id FROM jobs") == []
            kept = Registered(uuid4(), datetime(2026, 1, 1, tzinfo=UTC))
            async with database.transaction():
                await database.execute("INSERT INTO users VALUES (?)", (str(kept.user_id),))
                await bus.publish(kept)
            assert len(await database.fetch_all("SELECT id FROM jobs")) == 1
            await queue.on_application_bootstrap()
            assert await queue.drain(2)
            await queue.on_application_shutdown(None)
        assert seen == [kept]

    asyncio.run(scenario())


def test_a_handler_cannot_subscribe_two_times_to_one_event() -> None:
    bus = memory_event_bus()

    async def handle(event: Happened) -> None:
        return None

    bus.subscribe(Happened, handle)
    with pytest.raises(ValueError, match="subscribed"):
        bus.subscribe(Happened, handle)
