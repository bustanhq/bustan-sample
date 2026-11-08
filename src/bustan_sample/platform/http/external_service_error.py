from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx2

# A server can ask for a long wait. A job never waits longer than this for one retry.
MAX_RETRY_AFTER_SECONDS = 3600.0
_RETRYABLE_STATUSES = frozenset({408, 425, 429})


class ExternalServiceError(Exception):
    """An external service did not do the work.

    retryable tells if a retry can succeed: a timeout, a network error, 408,
    425, 429 or 5xx. It does not tell that a retry is safe. A POST without an
    idempotency key can do the work two times. retry_after gives the wait in
    seconds that the server asked for, if it asked.
    """

    def __init__(
        self,
        service: str,
        message: str,
        *,
        retryable: bool,
        status: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
        self.retryable = retryable
        self.status = status
        self.retry_after = retry_after


def raise_for_response(service: str, response: httpx2.Response) -> None:
    """Raise ExternalServiceError if the status is not 2xx.

    The message gives the method, the path and the status, never the body: a
    body can contain personal data.
    """
    if response.is_success:
        return
    status = response.status_code
    request = response.request
    raise ExternalServiceError(
        service,
        f"{request.method} {request.url.path} gave {status}",
        retryable=status in _RETRYABLE_STATUSES or status >= 500,
        status=status,
        retry_after=parse_retry_after(response.headers.get("retry-after")),
    )


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Return the seconds of a Retry-After header: a number or an HTTP date.

    Return None if the header is missing or not valid. The result is 0 to
    MAX_RETRY_AFTER_SECONDS.
    """
    if not value:
        return None
    text = value.strip()
    try:
        seconds = float(text)
    except ValueError:
        try:
            moment = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        seconds = (moment - (now or datetime.now(UTC))).total_seconds()
    if seconds != seconds:  # NaN
        return None
    return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)
