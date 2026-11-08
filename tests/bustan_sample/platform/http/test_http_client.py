import asyncio
import json
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager

import httpx2
import pytest
from bustan import Controller, Get, Module
from bustan.testing import AsgiTestClient, create_test_app

from bustan_sample.platform.http import (
    CORRELATION_HEADER,
    ExternalServiceError,
    HttpClient,
    HttpClientFactory,
)

type Handler = Callable[[httpx2.Request], httpx2.Response]


class _Api:
    """A fake external API. It keeps each request and answers with the handler."""

    def __init__(self, handler: Handler | None = None) -> None:
        self.requests: list[httpx2.Request] = []
        self._handler = handler or (lambda request: httpx2.Response(200, json={"ok": True}))

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self._handler(request)

    def client(self) -> HttpClient:
        factory = HttpClientFactory(httpx2.MockTransport(self))
        return factory.make(
            "example", "https://api.example.com/v1", headers={"Authorization": "Bearer top-secret"}
        )


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, object]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = json.loads(record.getMessage())
        except ValueError:
            return
        if payload.get("context") == "HttpClient":
            self.records.append(payload)


@contextmanager
def _http_records() -> Generator[list[dict[str, object]]]:
    handler = _Records()
    logger = logging.getLogger("bustan")
    logger.addHandler(handler)
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)


def test_a_call_goes_to_the_base_url_with_the_default_headers() -> None:
    async def scenario() -> None:
        api = _Api()
        client = api.client()
        response = await client.request("POST", "/emails", json={"to": "ada"})
        await client.aclose()
        assert response.status_code == 200
        [request] = api.requests
        assert str(request.url) == "https://api.example.com/v1/emails"
        assert request.headers["authorization"] == "Bearer top-secret"
        assert request.headers["user-agent"].startswith("bustan-sample")
        assert json.loads(request.content) == {"to": "ada"}
        assert CORRELATION_HEADER not in request.headers

    asyncio.run(scenario())


def test_a_4xx_or_a_5xx_response_comes_back_to_the_caller() -> None:
    async def scenario() -> None:
        for status in (404, 503):
            client = _Api(lambda request, status=status: httpx2.Response(status)).client()
            assert (await client.request("GET", "/x")).status_code == status
            await client.aclose()

    asyncio.run(scenario())


def _raises(error: type[httpx2.RequestError]) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error("failed in the test", request=request)

    return handler


@pytest.mark.parametrize(
    ("error", "retryable"),
    [
        (httpx2.ConnectTimeout, True),
        (httpx2.ReadTimeout, True),
        (httpx2.ConnectError, True),
        (httpx2.RemoteProtocolError, True),
        (httpx2.DecodingError, False),
    ],
)
def test_a_failed_call_raises_an_external_service_error(
    error: type[httpx2.RequestError], retryable: bool
) -> None:
    async def scenario() -> None:
        client = _Api(_raises(error)).client()
        with pytest.raises(ExternalServiceError) as caught:
            await client.request("GET", "/x")
        await client.aclose()
        assert caught.value.retryable is retryable
        assert caught.value.service == "example"
        assert isinstance(caught.value.__cause__, error)

    asyncio.run(scenario())


def test_each_call_writes_one_record_with_no_header_query_or_body() -> None:
    async def scenario() -> None:
        api = _Api(lambda request: httpx2.Response(201))
        client = api.client()
        await client.request("POST", "/emails?token=not-for-logs", json={"to": "ada@example.com"})
        failing = _Api(_raises(httpx2.ReadTimeout)).client()
        with pytest.raises(ExternalServiceError):
            await failing.request("GET", "/slow?token=not-for-logs")
        await client.aclose()
        await failing.aclose()

    with _http_records() as records:
        asyncio.run(scenario())
    done, failed = records
    assert (done["service"], done["method"], done["path"], done["status"]) == (
        "example",
        "POST",
        "/v1/emails",
        201,
    )
    assert isinstance(done["duration_ms"], int)
    assert (failed["path"], failed["error"]) == ("/slow", "timeout")
    text = json.dumps(records)
    for secret in ("top-secret", "not-for-logs", "ada@example.com"):
        assert secret not in text


@Controller("/probe")
class _ProbeController:
    api = _Api()

    @Get("/call")
    async def call(self) -> dict[str, str]:
        client = self.api.client()
        await client.request("GET", "/ping")
        await client.aclose()
        return {"status": "ok"}


@Module(controllers=[_ProbeController])
class _ProbeModule:
    pass


def test_a_call_in_a_request_sends_the_correlation_id_of_the_request() -> None:
    with AsgiTestClient(create_test_app(_ProbeModule)) as client:
        response = client.get("/probe/call", headers={"x-correlation-id": "request-42"})
    assert response.status_code == 200
    [request] = _ProbeController.api.requests
    assert request.headers[CORRELATION_HEADER] == "request-42"
