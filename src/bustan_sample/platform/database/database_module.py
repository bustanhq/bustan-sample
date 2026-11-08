from bustan import Module

from .database import Database


# Each module with an SQLite adapter imports this module. All of them get the
# same Database instance, thus the process has one connection. Database reads
# ConfigService, which the global ConfigModule of the root module gives.
@Module(providers=[Database], exports=[Database])
class DatabaseModule:
    pass
