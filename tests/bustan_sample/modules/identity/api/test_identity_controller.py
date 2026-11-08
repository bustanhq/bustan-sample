from collections.abc import Callable

from bustan.testing import AsgiTestClient
from support.fakes import RecordingMailer, wait_until

from bustan_sample.modules.identity.application.send_welcome_email_job import SUBJECT
from bustan_sample.platform.clock import FixedClock

SignUp = Callable[[str], dict[str, str]]
PASSWORD = "a long password for the tests"


def test_registration_sends_one_welcome_email_in_the_background(
    client: AsgiTestClient, mailer: RecordingMailer
) -> None:
    # The route answers first. The event handler and the job send the email.
    client.post(
        "/identity/register", json={"email": "ada@example.com", "password": PASSWORD}
    )
    wait_until(lambda: len(mailer.sent) == 1)
    [(to, subject, _)] = mailer.sent
    assert (to, subject) == ("ada@example.com", SUBJECT)


def test_a_refused_registration_sends_no_email(
    client: AsgiTestClient, mailer: RecordingMailer
) -> None:
    client.post(
        "/identity/register", json={"email": "ada@example.com", "password": "short"}
    )
    client.post(
        "/identity/register", json={"email": "not-an-email", "password": PASSWORD}
    )
    # The queue is empty when the next route answers: the two refusals
    # published nothing, thus nothing can arrive later.
    client.post(
        "/identity/register", json={"email": "bob@example.com", "password": PASSWORD}
    )
    wait_until(lambda: len(mailer.sent) >= 1)
    assert [to for to, _, _ in mailer.sent] == ["bob@example.com"]


def test_register_returns_201_without_the_password_hash(client: AsgiTestClient) -> None:
    response = client.post(
        "/identity/register", json={"email": "Ada@Example.com", "password": PASSWORD}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"
    assert set(response.json()) == {"id", "email", "created_at"}


def test_register_refuses_a_taken_email_and_a_weak_password(
    client: AsgiTestClient,
) -> None:
    client.post(
        "/identity/register", json={"email": "ada@example.com", "password": PASSWORD}
    )
    taken = client.post(
        "/identity/register", json={"email": "ADA@example.com", "password": PASSWORD}
    )
    weak = client.post(
        "/identity/register", json={"email": "bob@example.com", "password": "short"}
    )
    assert taken.status_code == 409
    assert weak.status_code == 400
    assert weak.headers["content-type"].startswith("application/problem+json")


def test_login_gives_a_bearer_token_that_expires(
    client: AsgiTestClient, clock: FixedClock
) -> None:
    credentials = {"email": "ada@example.com", "password": PASSWORD}
    client.post("/identity/register", json=credentials)
    response = client.post("/identity/login", json=credentials)
    body = response.json()
    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2
    assert body["expires_at"] > clock.now().isoformat()


def test_bad_credentials_give_401_with_one_message(client: AsgiTestClient) -> None:
    client.post(
        "/identity/register", json={"email": "ada@example.com", "password": PASSWORD}
    )
    wrong_password = client.post(
        "/identity/login", json={"email": "ada@example.com", "password": "x" * 20}
    )
    unknown_email = client.post(
        "/identity/login", json={"email": "bob@example.com", "password": PASSWORD}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_me_gives_the_user_of_the_token(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    response = client.get("/identity/me", headers=sign_up("ada@example.com"))
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_me_needs_a_valid_bearer_token(client: AsgiTestClient) -> None:
    headers = [
        {},
        {"authorization": "Bearer not-a-token"},
        {"authorization": "Basic YWRhOnB3"},
    ]
    responses = [client.get("/identity/me", headers=header) for header in headers]
    assert [response.status_code for response in responses] == [401] * 3
    assert responses[0].headers["www-authenticate"].startswith("Bearer")


def test_logout_revokes_the_token_before_it_expires(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    ada = sign_up("ada@example.com")
    other_session = sign_up("ada@example.com")
    assert client.post("/identity/logout", headers=ada).status_code == 204
    assert client.get("/identity/me", headers=ada).status_code == 401
    assert client.get("/tasks", headers=ada).status_code == 401
    assert client.post("/identity/logout", headers=ada).status_code == 401
    assert client.get("/identity/me", headers=other_session).status_code == 200
