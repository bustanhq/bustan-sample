"""Fixtures for all tests."""

import os
from collections.abc import Callable, Iterator

import pytest
from bustan.testing import AsgiTestClient, create_test_app

from bustan_sample.modules.identity.domain.password_hasher import PasswordHasher
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.platform.clock import Clock, FixedClock

# ConfigModule.for_root() in bustan_sample.app_module reads the environment
# when Python imports that file. pytest loads this file before the test files,
# thus the test settings are in the environment before that import. The
# environment overrides a local .env file.
os.environ["IDENTITY_JWT_SECRET"] = "a-test-secret-that-is-longer-than-32-characters"

PASSWORD = "a long password for the tests"

SignUp = Callable[[str], dict[str, str]]


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def client(clock: FixedClock) -> Iterator[AsgiTestClient]:
    """A client for the full application, with a fixed clock and a fast hasher."""
    from bustan_sample.app_module import AppModule

    app = create_test_app(
        AppModule,
        provider_overrides={
            Clock: clock,
            PasswordHasher: Argon2PasswordHasher.with_low_cost(),
        },
    )
    with AsgiTestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sign_up(client: AsgiTestClient) -> SignUp:
    """Return a function that registers a user, logs in and gives the auth header."""

    def _sign_up(email: str) -> dict[str, str]:
        credentials = {"email": email, "password": PASSWORD}
        client.post("/identity/register", json=credentials)
        token = client.post("/identity/login", json=credentials).json()["access_token"]
        return {"authorization": f"Bearer {token}"}

    return _sign_up
