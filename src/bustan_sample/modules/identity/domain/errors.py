from uuid import UUID


class IdentityError(Exception):
    """The base class of the errors of the identity domain."""


class InvalidUserError(IdentityError):
    """A value does not obey a rule for users, for example the password policy."""


class EmailTakenError(IdentityError):
    """A user with this email address exists."""

    def __init__(self) -> None:
        super().__init__("a user with this email address exists")


class InvalidCredentialsError(IdentityError):
    """The email address or the password is not correct.

    The message does not tell which of the two is incorrect.
    """

    def __init__(self) -> None:
        super().__init__("the email address or the password is not correct")


class UserNotFoundError(IdentityError):
    """No user has the given id."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"no user with id {user_id}")
        self.user_id = user_id
