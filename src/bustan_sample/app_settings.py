from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AppSettings(BaseModel):
    """The settings of the application, read from the environment and from .env.

    The application does not start if a value is missing or not valid. Each key
    starts with the name of the module that reads it.
    """

    # The process environment has many other variables. The model ignores them.
    model_config = ConfigDict(extra="ignore")

    DATABASE_BACKEND: Literal["memory", "sqlite"] = "memory"
    DATABASE_SQLITE_PATH: str = Field(default="var/bustan-sample.db", min_length=1)

    IDENTITY_JWT_SECRET: str = Field(min_length=32)
    IDENTITY_JWT_ISSUER: str = Field(default="bustan-sample", min_length=1)
    IDENTITY_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1, le=1440)

    JOBS_WORKERS: int = Field(default=2, ge=1, le=32)
    JOBS_RETRY_DELAY_SECONDS: float = Field(default=1.0, ge=0, le=300)
    JOBS_POLL_SECONDS: float = Field(default=0.5, gt=0, le=60)
    JOBS_LEASE_SECONDS: float = Field(default=300, ge=1, le=86400)
    JOBS_SCHEDULER_ENABLED: bool = True

    MAIL_BACKEND: Literal["log", "resend"] = "log"
    MAIL_FROM: str = ""
    MAIL_RESEND_API_KEY: str = ""

    @model_validator(mode="after")
    def _resend_has_a_key_and_a_sender(self) -> Self:
        if self.MAIL_BACKEND == "resend" and not (self.MAIL_RESEND_API_KEY and self.MAIL_FROM):
            raise ValueError("MAIL_BACKEND=resend requires MAIL_RESEND_API_KEY and MAIL_FROM")
        return self
