from bustan import ConfigService, FactoryProvider, Module

from bustan_sample.platform.http import HttpClientFactory, HttpModule

from .log_mailer import LogMailer
from .mailer import Mailer
from .resend_mailer import ResendMailer


def _mailer(config: ConfigService, http: HttpClientFactory) -> Mailer:
    if str(config.get("MAIL_BACKEND", "log")) == "resend":
        return ResendMailer(
            http,
            api_key=str(config.get("MAIL_RESEND_API_KEY", "")),
            sender=str(config.get("MAIL_FROM", "")),
        )
    return LogMailer()


# MAIL_BACKEND selects the adapter of Mailer: log (the default) writes a log
# record, and resend sends the email through the Resend API. The factory makes
# only the selected adapter, and bustan runs the hooks of that adapter.
@Module(
    imports=[HttpModule],
    providers=[
        FactoryProvider(
            provide=Mailer, use_factory=_mailer, inject=(ConfigService, HttpClientFactory)
        ),
    ],
    exports=[Mailer],
)
class MailModule:
    pass
