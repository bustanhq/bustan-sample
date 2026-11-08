import asyncio
from pathlib import Path

from bustan import ConfigService

from bustan_sample.platform.database import Database
from bustan_sample.platform.health import DatabaseIndicator

from support.database import open_sqlite


def test_an_open_database_is_up(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "test.db") as database:
            result = await DatabaseIndicator(database).check()
        assert result.status.value == "up"

    asyncio.run(scenario())


def test_a_database_that_is_not_open_is_down_with_no_details() -> None:
    async def scenario() -> None:
        database = Database(ConfigService({"DATABASE_BACKEND": "sqlite"}))
        result = await DatabaseIndicator(database).check()
        assert result.status.value == "down"
        assert result.detail == "the database does not answer"

    asyncio.run(scenario())
