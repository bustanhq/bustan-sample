from bustan import ConfigModule, HealthModule, Module, ThrottlerModule

from .app_settings import AppSettings
from .modules.identity import IdentityModule
from .modules.tasks import TasksModule
from .platform.health import HealthChecksModule
from .platform.request_logging import RequestLoggingModule
from .platform.throttling import (
    GLOBAL_LIMIT,
    GLOBAL_TTL_SECONDS,
    THROTTLER_STORAGE,
    ThrottlingModule,
)


# The root module composes the application. It imports the configuration,
# the platform modules that apply to all routes, and the feature modules. It
# has no providers or controllers of its own.
#
# ConfigModule.for_root() reads .env and the environment when Python imports
# this file. If a setting is missing or not valid, the import fails.
# ThrottlerModule.for_root() limits each client to GLOBAL_LIMIT requests in
# GLOBAL_TTL_SECONDS. ThrottlingModule binds its storage to the database.
# HealthModule serves /health/live and /health/ready. The probes are not
# throttled.
@Module(
    imports=[
        ConfigModule.for_root(env_file=".env", validation_schema=AppSettings),
        HealthModule.for_root(check_timeout=2.0),
        ThrottlerModule.for_root(
            ttl=GLOBAL_TTL_SECONDS, limit=GLOBAL_LIMIT, storage=THROTTLER_STORAGE
        ),
        ThrottlingModule,
        HealthChecksModule,
        RequestLoggingModule,
        IdentityModule,
        TasksModule,
    ]
)
class AppModule:
    pass
