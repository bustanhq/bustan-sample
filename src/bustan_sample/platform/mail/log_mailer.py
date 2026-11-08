from bustan import Injectable, Logger, LogLevel

from .mailer import Mailer


@Injectable()
class LogMailer(Mailer):
    """Writes a log record in place of an email, for development.

    The record gives the subject and a masked recipient. It never gives the
    body, because a body can contain personal data or a secret link.
    """

    def __init__(self) -> None:
        self._logger = Logger("LogMailer")

    async def send(self, to: str, subject: str, body: str) -> None:
        self._logger.record(
            LogLevel.LOG,
            "mail sent",
            fields={
                "to": mask_address(to),
                "subject": subject,
                "body_chars": len(body),
            },
        )


def mask_address(address: str) -> str:
    """Return the address with all characters of the local part after the first masked."""
    local, at, domain = address.partition("@")
    if not at:
        return "***"
    return f"{local[:1]}***@{domain}"
