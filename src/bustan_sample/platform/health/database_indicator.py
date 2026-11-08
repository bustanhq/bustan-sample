from bustan import HealthIndicatorResult, Injectable

from bustan_sample.platform.database import Database


@Injectable()
class DatabaseIndicator:
    """The readiness check of the SQLite database. It runs SELECT 1.

    The detail of a failure crosses a trust boundary: each caller of the probe
    can read it. Thus it never contains the path or the error text.
    """

    name = "database"

    def __init__(self, database: Database) -> None:
        self._database = database

    async def check(self) -> HealthIndicatorResult:
        try:
            await self._database.fetch_one("SELECT 1")
        # Any error means that the process cannot serve requests that need data.
        except Exception:  # noqa: BLE001
            return HealthIndicatorResult.down("the database does not answer")
        return HealthIndicatorResult.up()
