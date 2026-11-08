from bustan import HealthService, Injectable, Module

from bustan_sample.platform.database import Database, DatabaseModule

from .database_indicator import DatabaseIndicator


@Injectable()
class HealthChecks:
    """Registers the readiness checks of the platform. Liveness gets no check.

    A failed dependency must not restart a process that works, thus the
    database check goes to readiness only, and only with the SQLite backend.
    """

    def __init__(
        self, health: HealthService, database: Database, indicator: DatabaseIndicator
    ) -> None:
        self._health = health
        self._database = database
        self._indicator = indicator

    def on_module_init(self) -> None:
        if self._database.is_sqlite:
            self._health.register_readiness(self._indicator)


# The root module imports HealthModule.for_root(), which is global and gives
# HealthService, and this module. HealthModule serves GET /health/live and
# GET /health/ready.
@Module(imports=[DatabaseModule], providers=[DatabaseIndicator, HealthChecks])
class HealthChecksModule:
    pass
