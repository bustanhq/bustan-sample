import asyncio
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

import pytest
from bustan.testing import AsgiTestClient, create_testing_module

from bustan_sample.app_module import AppModule

SignUp = Callable[[str], dict[str, str]]


async def _served_routes() -> set[tuple[object, object]]:
    compiled = await create_testing_module(AppModule).compile()
    try:
        return {(route["controller"], route["path"]) for route in compiled.snapshot_routes()}
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


def test_the_backend_selects_where_the_data_goes(
    client: AsgiTestClient,
    sign_up: SignUp,
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    sign_up("ada@example.com")
    database = tmp_path / "app.db"
    if request.node.callspec.params["client"] == "memory":
        assert not database.exists()
        return
    with closing(sqlite3.connect(database)) as connection:
        users = connection.execute("SELECT email FROM users").fetchall()
        tasks = connection.execute("SELECT title FROM tasks").fetchall()
    assert users == [("ada@example.com",)]
    assert len(tasks) == 1


def test_the_probes_answer_up_without_a_token(client: AsgiTestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    assert (live.status_code, ready.status_code) == (200, 200)
    assert ready.json()["status"] == "up"


def test_the_readiness_probe_checks_the_database_only_with_sqlite(
    client: AsgiTestClient, request: pytest.FixtureRequest
) -> None:
    checks = client.get("/health/ready").json()["checks"]
    backend = request.node.callspec.params["client"]
    assert ("database" in checks) is (backend == "sqlite")
