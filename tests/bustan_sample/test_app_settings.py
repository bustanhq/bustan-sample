import os

import pytest
from pydantic import ValidationError

from bustan_sample.app_settings import AppSettings


def _settings(**values: str) -> AppSettings:
    return AppSettings.model_validate({**os.environ, **values})


def test_the_defaults_need_only_the_jwt_secret() -> None:
    settings = _settings()
    assert (settings.DATABASE_BACKEND, settings.MAIL_BACKEND) == ("memory", "log")


@pytest.mark.parametrize(
    "values",
    [
        {"MAIL_BACKEND": "resend"},
        {"MAIL_BACKEND": "resend", "MAIL_FROM": "noreply@example.com"},
        {"MAIL_BACKEND": "resend", "MAIL_RESEND_API_KEY": "test-api-key"},
    ],
)
def test_the_resend_backend_needs_a_key_and_a_sender(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="MAIL_RESEND_API_KEY and MAIL_FROM"):
        _settings(**values)


def test_a_short_jwt_secret_stops_the_start() -> None:
    with pytest.raises(ValidationError, match="IDENTITY_JWT_SECRET"):
        _settings(IDENTITY_JWT_SECRET="short")
