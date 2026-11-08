import asyncio
import os

from bustan import ConfigModule, ConfigService, Module
from bustan.testing import create_testing_module

from bustan_sample.app_settings import AppSettings
from bustan_sample.platform.mail import LogMailer, Mailer, MailModule, ResendMailer


@Module(
    imports=[
        ConfigModule.for_root(ignore_env_file=True, validation_schema=AppSettings),
        MailModule,
    ]
)
class _TestRoot:
    pass


def _mailer_type(**values: str) -> type[Mailer]:
    async def scenario() -> type[Mailer]:
        settings = AppSettings.model_validate({**os.environ, **values}).model_dump()
        builder = create_testing_module(_TestRoot)
        builder.override_provider(ConfigService).use_value(ConfigService(settings))
        compiled = await builder.compile()
        try:
            return type(compiled.get(Mailer))
        finally:
            await compiled.close()

    return asyncio.run(scenario())


def test_the_log_mailer_is_the_default() -> None:
    assert _mailer_type() is LogMailer


def test_mail_backend_resend_selects_the_resend_mailer() -> None:
    mailer = _mailer_type(
        MAIL_BACKEND="resend",
        MAIL_FROM="bustan-sample <noreply@example.com>",
        MAIL_RESEND_API_KEY="test-api-key",
    )
    assert mailer is ResendMailer
