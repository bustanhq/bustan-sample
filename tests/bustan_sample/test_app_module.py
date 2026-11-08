import asyncio

from bustan.testing import create_testing_module

from bustan_sample.app_module import AppModule


async def _served_routes() -> set[tuple[object, object]]:
    compiled = await create_testing_module(AppModule).compile()
    try:
        return {
            (route["controller"], route["path"]) for route in compiled.snapshot_routes()
        }
    finally:
        await compiled.close()


def test_app_module_serves_the_identity_and_task_routes() -> None:
    # Compile and close are async. The project uses pytest without an async
    # plugin, thus the test runs the coroutine itself.
    served = asyncio.run(_served_routes())
    assert {
        ("IdentityController", "/identity/register"),
        ("IdentityController", "/identity/login"),
        ("IdentityController", "/identity/logout"),
        ("IdentityController", "/identity/me"),
        ("TasksController", "/tasks"),
        ("TasksController", "/tasks/{task_id}"),
    } <= served
