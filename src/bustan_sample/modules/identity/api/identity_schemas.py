from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..domain.token_issuer import AccessToken
from ..domain.user import EMAIL_MAX_LENGTH, PASSWORD_MAX_LENGTH, User

# The schemas set only upper limits for the length. The domain applies the
# email and password rules, thus the rules have one source.


class RegisterRequest(BaseModel):
    """The JSON body of POST /identity/register."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class LogInRequest(BaseModel):
    """The JSON body of POST /identity/login."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime

    @classmethod
    def from_token(cls, token: AccessToken) -> Self:
        return cls(access_token=token.value, expires_at=token.expires_at)

    def to_json(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class UserResponse(BaseModel):
    """The JSON shape of a user. It never contains the password hash."""

    id: UUID
    email: str
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> Self:
        return cls(id=user.id, email=user.email, created_at=user.created_at)

    def to_json(self) -> dict[str, object]:
        return self.model_dump(mode="json")
