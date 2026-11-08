"""Fixtures for all tests."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from bustan import ConfigService
from bustan.testing import AsgiTestClient, create_test_app
from support.database import BACKENDS
from support.fakes import RecordingMailer, wait_until

from bustan_sample.modules.identity.domain.password_hasher import PasswordHasher
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.platform.clock import Clock, FixedClock
from bustan_sample.platform.mail import Mailer

# ConfigModule.for_root() in bustan_sample.app_module reads the environment
# when Python imports that file. pytest loads this file before the test files,
# thus the test settings are in the environment before that import. The
# environment overrides a local .env file.
os.environ["IDENTITY_JWT_SECRET"] = "a-test-secret-that-is-longer-than-32-characters"
os.environ["DATABASE_BACKEND"] = "memory"
os.environ["JOBS_RETRY_DELAY_SECONDS"] = "0"
os.environ["JOBS_POLL_SECONDS"] = "0.01"

PASSWORD = "a long password for the tests"

SignUp = Callable[[str], dict[str, str]]


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest.fixture(params=BACKENDS)
def client(
    request: pytest.FixtureRequest,
    clock: FixedClock,
    mailer: RecordingMailer,
    tmp_path: Path,
) -> Iterator[AsgiTestClient]:
    """A client for the full application, once for each database backend.

    The application has a fixed clock, a fast hasher and a mailer that records
    the messages. The events and the jobs run as in production. For the sqlite
    backend, a ConfigService override selects a new database file. The import
    of the root module read the environment before, thus an environment change
    here has no effect.
    """
    from bustan_sample.app_module import AppModule
    from bustan_sample.app_settings import AppSettings

    overrides: dict[object, object] = {
        Clock: clock,
        PasswordHasher: Argon2PasswordHasher.with_low_cost(),
        Mailer: mailer,
    }
    if request.param == "sqlite":
        values = {
            **os.environ,
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_SQLITE_PATH": str(tmp_path / "app.db"),
        }
        overrides[ConfigService] = ConfigService(
            AppSettings.model_validate(values).model_dump()
        )
    app = create_test_app(AppModule, provider_overrides=overrides)
    with AsgiTestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sign_up(client: AsgiTestClient) -> SignUp:
    """Return a function that registers a user, logs in and gives the auth header.

    The function waits for the starter task that the tasks module adds in the
    background. Thus the starter task is always the first task of the user.
    """

    def _sign_up(email: str) -> dict[str, str]:
        credentials = {"email": email, "password": PASSWORD}
        client.post("/identity/register", json=credentials)
        token = client.post("/identity/login", json=credentials).json()["access_token"]
        headers = {"authorization": f"Bearer {token}"}
        wait_until(lambda: len(client.get("/tasks", headers=headers).json()) > 0)
        return headers

    return _sign_up
