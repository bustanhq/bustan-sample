from datetime import UTC, datetime

import httpx2
import pytest

from bustan_sample.platform.http import (
    MAX_RETRY_AFTER_SECONDS,
    ExternalServiceError,
    parse_retry_after,
    raise_for_response,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def _response(status: int, headers: dict[str, str] | None = None) -> httpx2.Response:
    request = httpx2.Request("POST", "https://api.example.com/emails?token=not-for-logs")
    return httpx2.Response(status, headers=headers, request=request)


def test_a_2xx_response_raises_nothing() -> None:
    for status in (200, 201, 202, 204):
        raise_for_response("mail", _response(status))


@pytest.mark.parametrize(
    ("status", "retryable"),
    [
        (400, False),
        (401, False),
        (403, False),
        (404, False),
        (409, False),
        (422, False),
        (408, True),
        (425, True),
        (429, True),
        (500, True),
        (502, True),
        (503, True),
    ],
)
def test_the_status_tells_if_a_retry_can_succeed(status: int, retryable: bool) -> None:
    with pytest.raises(ExternalServiceError) as caught:
        raise_for_response("mail", _response(status))
    assert caught.value.retryable is retryable
    assert caught.value.status == status
    assert caught.value.service == "mail"


def test_the_message_gives_the_path_but_not_the_query() -> None:
    with pytest.raises(ExternalServiceError, match="mail: POST /emails gave 500") as caught:
        raise_for_response("mail", _response(500))
    assert "not-for-logs" not in str(caught.value)


def test_the_error_keeps_the_retry_after_of_the_server() -> None:
    with pytest.raises(ExternalServiceError) as caught:
        raise_for_response("mail", _response(429, {"Retry-After": "7"}))
    assert caught.value.retry_after == 7.0


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        (None, None),
        ("", None),
        ("12", 12.0),
        (" 1.5 ", 1.5),
        ("-3", 0.0),
        ("999999", MAX_RETRY_AFTER_SECONDS),
        ("Sun, 08 Nov 2026 12:00:30 GMT", 30.0),
        ("Sun, 08 Nov 2026 11:59:00 GMT", 0.0),
        ("soon", None),
        ("nan", None),
    ],
)
def test_retry_after_is_a_number_or_an_http_date(value: str | None, seconds: float | None) -> None:
    assert parse_retry_after(value, NOW) == seconds
