from datetime import UTC, datetime

import pytest

from bustan_sample.modules.identity.domain.errors import InvalidUserError
from bustan_sample.modules.identity.domain.user import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    User,
    check_password_policy,
    normalize_email,
)


def test_a_new_user_has_a_normalized_email() -> None:
    user = User.create("  Ada@Example.COM ", "hash", datetime(2026, 1, 1, tzinfo=UTC))
    assert user.email == "ada@example.com"


@pytest.mark.parametrize(
    "email", ["", "ada", "@example.com", "ada@", "ada@example", "a da@example.com"]
)
def test_an_invalid_email_is_refused(email: str) -> None:
    with pytest.raises(InvalidUserError):
        normalize_email(email)


@pytest.mark.parametrize(
    "password", ["x" * (PASSWORD_MIN_LENGTH - 1), "x" * (PASSWORD_MAX_LENGTH + 1)]
)
def test_a_password_out_of_the_policy_is_refused(password: str) -> None:
    with pytest.raises(InvalidUserError):
        check_password_policy(password)


def test_a_password_in_the_policy_is_accepted() -> None:
    check_password_policy("x" * PASSWORD_MIN_LENGTH)
