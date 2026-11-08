import json

import httpx2

from bustan_sample.platform.http import (
    ExternalServiceError,
    HttpClient,
    HttpClientFactory,
    parse_retry_after,
    raise_for_response,
)

from .mailer import Mailer

RESEND_API_URL = "https://api.resend.com"
SERVICE = "resend"
# Resend refuses a longer key.
MAX_IDEMPOTENCY_KEY_LENGTH = 256
# A 409 with this name: the same key came with a different message. A retry
# gets the same answer. Each other 409 is a request in progress or a locked
# resource, and a retry can succeed.
_KEY_REUSED = "invalid_idempotent_request"


class ResendMailer(Mailer):
    """Sends email through the Resend API, with POST /emails.

    The API key goes in the Authorization header. The idempotency key goes in
    the Idempotency-Key header. Resend keeps a key for 24 hours and sends no
    second email with the same key. Thus a retry after a lost response, or
    after a stop between the send and the commit of the job, sends one email.

    on_module_init makes the client. on_module_destroy closes it, after the
    job queue stopped in on_application_shutdown.
    """

    def __init__(self, http: HttpClientFactory, api_key: str, sender: str) -> None:
        if not api_key or not sender:
            raise ValueError("the Resend mailer requires an API key and a sender address")
        self._http = http
        self._api_key = api_key
        self._sender = sender
        self._client: HttpClient | None = None

    async def on_module_init(self) -> None:
        self._client = self._http.make(
            SERVICE, RESEND_API_URL, headers={"Authorization": f"Bearer {self._api_key}"}
        )

    async def on_module_destroy(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send(
        self, to: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            if not 0 < len(idempotency_key) <= MAX_IDEMPOTENCY_KEY_LENGTH:
                raise ValueError(
                    f"an idempotency key has 1 to {MAX_IDEMPOTENCY_KEY_LENGTH} characters"
                )
            headers["Idempotency-Key"] = idempotency_key
        message = {"from": self._sender, "to": [to], "subject": subject, "text": body}
        response = await self._started().request("POST", "/emails", json=message, headers=headers)
        if response.status_code == 409:
            name = _error_name(response)
            raise ExternalServiceError(
                SERVICE,
                f"POST /emails gave 409 {name}",
                retryable=name != _KEY_REUSED,
                status=409,
                retry_after=parse_retry_after(response.headers.get("retry-after")),
            )
        raise_for_response(SERVICE, response)

    def _started(self) -> HttpClient:
        if self._client is None:
            raise RuntimeError("the Resend mailer is not started")
        return self._client


def _error_name(response: httpx2.Response) -> str:
    """Return the field name of the error body, or "unknown"."""
    try:
        body = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "unknown"
    name = body.get("name") if isinstance(body, dict) else None
    return name if isinstance(name, str) else "unknown"
