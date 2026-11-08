from bustan import Injectable, Module

from bustan_sample.platform.database import Database, DatabaseModule

from .backend_throttler_storage import BackendThrottlerStorage

THROTTLER_STORAGE = BackendThrottlerStorage()
"""The one storage that the root module gives to ThrottlerModule.for_root()."""

GLOBAL_TTL_SECONDS = 60
GLOBAL_LIMIT = 300


@Injectable()
class ThrottlerStorageBinding:
    """Binds THROTTLER_STORAGE to the Database of the application that starts.

    Two applications in one process share THROTTLER_STORAGE. Thus run only one
    application at a time in a process, as the server and the tests do.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await THROTTLER_STORAGE.bind(self._database)

    def on_module_destroy(self) -> None:
        THROTTLER_STORAGE.unbind()


@Module(imports=[DatabaseModule], providers=[ThrottlerStorageBinding])
class ThrottlingModule:
    pass
