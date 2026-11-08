from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    """The settings of the application, read from the environment and from .env.

    The application does not start if a value is missing or not valid. Each key
    starts with the name of the module that reads it.
    """

    # The process environment has many other variables. The model ignores them.
    model_config = ConfigDict(extra="ignore")

    IDENTITY_JWT_SECRET: str = Field(min_length=32)
    IDENTITY_JWT_ISSUER: str = Field(default="bustan-sample", min_length=1)
    IDENTITY_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1, le=1440)

    JOBS_WORKERS: int = Field(default=2, ge=1, le=32)
    JOBS_RETRY_DELAY_SECONDS: float = Field(default=1.0, ge=0, le=300)
