import time
from collections.abc import Mapping

import httpx2
from bustan import Logger, LogLevel
from bustan.observability import current_correlation_id

from .external_service_error import ExternalServiceError

CORRELATION_HEADER = "x-correlation-id"


class HttpClient:
    """The client of one external API, made by HttpClientFactory.

    request() returns each response, also a 4xx or a 5xx: the adapter reads
    the status, or calls raise_for_response(). A timeout or a network error
    raises ExternalServiceError, thus an adapter never handles an httpx2
    error. The client does not retry: the caller decides. In a job, the job
    queue retries.

    If a request is in flight, each call sends its correlation id, thus the
    logs of the two services join. Each call writes one log record with the
    service, the method, the path, the status and the duration. The record
    never contains a header, a query or a body.
    """

    def __init__(self, service: str, client: httpx2.AsyncClient) -> None:
        self.service = service
        self._client = client
        self._logger = Logger("HttpClient")

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: object = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx2.Response:
        all_headers = dict(headers or {})
        correlation_id = current_correlation_id()
        if correlation_id is not None:
            all_headers.setdefault(CORRELATION_HEADER, correlation_id)
        started = time.perf_counter()
        try:
            response = await self._client.request(method, path, json=json, headers=all_headers)
        except httpx2.TimeoutException as exc:
            raise self._failure(method, path, started, "timeout", exc, retryable=True) from exc
        except httpx2.TransportError as exc:
            reason = type(exc).__name__
            raise self._failure(method, path, started, reason, exc, retryable=True) from exc
        except httpx2.RequestError as exc:
            reason = type(exc).__name__
            raise self._failure(method, path, started, reason, exc, retryable=False) from exc
        self._logger.record(
            LogLevel.LOG,
            "external call",
            fields={
                "service": self.service,
                "method": method,
                "path": response.request.url.path,
                "status": response.status_code,
                "duration_ms": _elapsed_ms(started),
            },
        )
        return response

    async def aclose(self) -> None:
        await self._client.aclose()

    def _failure(
        self,
        method: str,
        path: str,
        started: float,
        reason: str,
        exc: Exception,
        *,
        retryable: bool,
    ) -> ExternalServiceError:
        self._logger.record(
            LogLevel.WARN,
            "external call failed",
            fields={
                "service": self.service,
                "method": method,
                "path": path.partition("?")[0],
                "error": reason,
                "duration_ms": _elapsed_ms(started),
            },
        )
        return ExternalServiceError(self.service, f"{method} {path}: {reason}", retryable=retryable)


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
