import asyncio

from bustan import ConfigModule, Module
from bustan.testing import create_testing_module

from bustan_sample.app_settings import AppSettings
from bustan_sample.modules.tasks import TasksModule


# TasksModule imports IdentityModule, which reads ConfigService from the global
# ConfigModule of the root module. Thus the test root gives only a
# ConfigModule. The secret comes from the environment that conftest.py sets.
@Module(
    imports=[
        ConfigModule.for_root(ignore_env_file=True, validation_schema=AppSettings),
        TasksModule,
    ]
)
class _TestRoot:
    pass


async def _served_routes() -> set[object]:
    compiled = await create_testing_module(_TestRoot).compile()
    try:
        return {route["path"] for route in compiled.snapshot_routes()}
    finally:
        await compiled.close()


def test_the_module_compiles_with_only_config_beside_it() -> None:
    served = asyncio.run(_served_routes())
    assert {"/tasks", "/tasks/{task_id}"} <= served
