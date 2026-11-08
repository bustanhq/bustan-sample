import asyncio

from bustan import AUTHENTICATOR_REGISTRY, ConfigModule, Module
from bustan.testing import create_testing_module

from bustan_sample.app_settings import AppSettings
from bustan_sample.modules.identity import STRATEGY, IdentityModule
from bustan_sample.modules.identity.api.bearer_authenticator import BearerAuthenticator


# IdentityModule reads ConfigService from the global ConfigModule of the root
# module. Thus the test root gives the module only a ConfigModule. The secret
# comes from the environment that conftest.py sets.
@Module(
    imports=[
        ConfigModule.for_root(ignore_env_file=True, validation_schema=AppSettings),
        IdentityModule,
    ]
)
class _TestRoot:
    pass


async def _check_module() -> None:
    compiled = await create_testing_module(_TestRoot).compile()
    try:
        registry = compiled.get(AUTHENTICATOR_REGISTRY)
        assert isinstance(registry[STRATEGY], BearerAuthenticator)
        served = {route["path"] for route in compiled.snapshot_routes()}
        assert {"/identity/register", "/identity/login", "/identity/me"} <= served
    finally:
        await compiled.close()


def test_the_module_needs_only_config_and_exports_the_bearer_strategy() -> None:
    asyncio.run(_check_module())
