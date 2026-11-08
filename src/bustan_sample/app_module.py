from bustan import ConfigModule, Module

from .app_settings import AppSettings
from .modules.identity import IdentityModule
from .modules.tasks import TasksModule
from .platform.request_logging import RequestLoggingModule


# The root module composes the application. It imports the configuration,
# the platform modules that apply to all routes, and the feature modules. It
# has no providers or controllers of its own.
#
# ConfigModule.for_root() reads .env and the environment when Python imports
# this file. If a setting is missing or not valid, the import fails.
@Module(
    imports=[
        ConfigModule.for_root(env_file=".env", validation_schema=AppSettings),
        RequestLoggingModule,
        IdentityModule,
        TasksModule,
    ]
)
class AppModule:
    pass
