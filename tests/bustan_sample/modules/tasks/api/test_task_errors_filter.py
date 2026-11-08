from bustan.testing import AsgiTestClient, create_test_app

from bustan_sample.app_module import AppModule
from bustan_sample.modules.identity.domain.password_hasher import PasswordHasher
from bustan_sample.modules.identity.infra.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from bustan_sample.modules.tasks.application.create_task_command import (
    CreateTaskCommand,
    CreateTaskHandler,
)
from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
from bustan_sample.modules.tasks.domain.task import Task

CREDENTIALS = {"email": "ada@example.com", "password": "a long password for the tests"}


class _RefusingCreateHandler:
    async def execute(self, command: CreateTaskCommand) -> Task:
        raise InvalidTaskError("the domain refused the task")


def test_an_invalid_task_error_returns_400_problem_details() -> None:
    # The request schema refuses bad input before the domain sees it. Thus the
    # test replaces the handler to make the domain error occur.
    app = create_test_app(
        AppModule,
        provider_overrides={
            CreateTaskHandler: _RefusingCreateHandler(),
            PasswordHasher: Argon2PasswordHasher.with_low_cost(),
        },
    )
    with AsgiTestClient(app) as client:
        client.post("/identity/register", json=CREDENTIALS)
        token = client.post("/identity/login", json=CREDENTIALS).json()["access_token"]
        response = client.post(
            "/tasks", headers={"authorization": f"Bearer {token}"}, json={"title": "a"}
        )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "the domain refused the task"
