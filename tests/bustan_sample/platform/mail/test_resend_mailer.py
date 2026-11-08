import asyncio
import json

import httpx2
import pytest

from bustan_sample.platform.http import ExternalServiceError, HttpClientFactory
from bustan_sample.platform.mail import ResendMailer

SENDER = "bustan-sample <noreply@example.com>"
KEY = "identity.welcome_email:user-1"


class _Resend:
    """A fake Resend API. It keeps each request and gives the next answer."""

    def __init__(self, *answers: httpx2.Response | type[httpx2.RequestError]) -> None:
        self.requests: list[httpx2.Request] = []
        self._answers = list(answers) or [httpx2.Response(200, json={"id": "email-1"})]

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        answer = self._answers.pop(0)
        if isinstance(answer, httpx2.Response):
            return answer
        raise answer("failed in the test", request=request)

    async def mailer(self) -> ResendMailer:
        factory = HttpClientFactory(httpx2.MockTransport(self))
        mailer = ResendMailer(factory, api_key="test-api-key", sender=SENDER)
        await mailer.on_module_init()
        return mailer


def _error(status: int, name: str | None = None, **headers: str) -> httpx2.Response:
    body = {"statusCode": status, "name": name, "message": "test"} if name else None
    return httpx2.Response(status, json=body, headers=headers)


def test_a_send_posts_one_email_with_the_key() -> None:
    async def scenario() -> None:
        resend = _Resend()
        mailer = await resend.mailer()
        await mailer.send("ada@example.com", "Welcome", "Hello", idempotency_key=KEY)
        await mailer.on_module_destroy()
        [request] = resend.requests
        assert (request.method, str(request.url)) == ("POST", "https://api.resend.com/emails")
        assert request.headers["authorization"] == "Bearer test-api-key"
        assert request.headers["idempotency-key"] == KEY
        assert json.loads(request.content) == {
            "from": SENDER,
            "to": ["ada@example.com"],
            "subject": "Welcome",
            "text": "Hello",
        }

    asyncio.run(scenario())


def test_a_send_with_no_key_sends_no_idempotency_header() -> None:
    async def scenario() -> None:
        resend = _Resend()
        mailer = await resend.mailer()
        await mailer.send("ada@example.com", "Welcome", "Hello")
        assert "idempotency-key" not in resend.requests[0].headers

    asyncio.run(scenario())


def test_a_key_longer_than_256_characters_is_refused_before_the_call() -> None:
    async def scenario() -> None:
        resend = _Resend()
        mailer = await resend.mailer()
        with pytest.raises(ValueError, match="256"):
            await mailer.send("ada@example.com", "Welcome", "Hello", idempotency_key="k" * 257)
        assert resend.requests == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("answer", "retryable", "retry_after"),
    [
        (_error(409, "concurrent_idempotent_requests"), True, None),
        (_error(409, "resource_locked"), True, None),
        (_error(409, "invalid_idempotent_request"), False, None),
        (httpx2.Response(409, text="not json"), True, None),
        (_error(429, "rate_limit_exceeded", **{"retry-after": "2"}), True, 2.0),
        (_error(422, "missing_required_field"), False, None),
        (_error(403, "invalid_permission"), False, None),
        (_error(500, "application_error"), True, None),
        (httpx2.ReadTimeout, True, None),
    ],
)
def test_a_failed_send_tells_if_a_retry_can_succeed(
    answer: httpx2.Response | type[httpx2.RequestError],
    retryable: bool,
    retry_after: float | None,
) -> None:
    async def scenario() -> None:
        mailer = await _Resend(answer).mailer()
        with pytest.raises(ExternalServiceError) as caught:
            await mailer.send("ada@example.com", "Welcome", "Hello", idempotency_key=KEY)
        assert (caught.value.retryable, caught.value.retry_after) == (retryable, retry_after)
        assert caught.value.service == "resend"
        assert "ada@example.com" not in str(caught.value)

    asyncio.run(scenario())


def test_the_mailer_needs_a_key_a_sender_and_a_start() -> None:
    factory = HttpClientFactory(httpx2.MockTransport(_Resend()))
    with pytest.raises(ValueError, match="API key"):
        ResendMailer(factory, api_key="", sender=SENDER)
    with pytest.raises(ValueError, match="sender"):
        ResendMailer(factory, api_key="test-api-key", sender="")
    mailer = ResendMailer(factory, api_key="test-api-key", sender=SENDER)
    with pytest.raises(RuntimeError, match="not started"):
        asyncio.run(mailer.send("ada@example.com", "Welcome", "Hello"))
