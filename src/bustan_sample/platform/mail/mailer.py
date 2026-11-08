from abc import ABC, abstractmethod


class Mailer(ABC):
    """The port that sends email."""

    @abstractmethod
    async def send(
        self, to: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        """Send one plain-text message.

        Give idempotency_key to let the provider refuse a second send of the
        same message, for example after a retry. If the send fails, raise
        ExternalServiceError (bustan_sample.platform.http): its retryable flag
        tells if a retry can succeed.
        """
