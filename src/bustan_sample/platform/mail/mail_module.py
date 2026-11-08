from bustan import ClassProvider, Module

from .log_mailer import LogMailer
from .mailer import Mailer


# To send real email, bind Mailer to an adapter for an SMTP server or a mail
# API here.
@Module(
    providers=[ClassProvider(provide=Mailer, use_class=LogMailer)],
    exports=[Mailer],
)
class MailModule:
    pass
