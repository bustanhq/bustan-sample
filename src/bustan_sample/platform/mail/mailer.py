from abc import ABC, abstractmethod


class Mailer(ABC):
    """The port that sends email."""

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None:
        """Send one plain-text message. Raise an error if the send fails."""
