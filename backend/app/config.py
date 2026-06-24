"""Application settings."""

import secrets
import warnings
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).parent.parent.parent


def parse_cors(v: Any) -> list[str] | str:
    """Parse comma-separated CORS origins from environment variables."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    if isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / "envs" / "example.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str,
        BeforeValidator(parse_cors),
    ] = []

    PROJECT_NAME: str = "FastAPI DDD Backend"
    SENTRY_DSN: HttpUrl | None = None

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "app"

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

    REDIS_URL: str = "redis://localhost:6379/0"
    ARQ_QUEUE_NAME: str = "skills-dddpy-tasks"
    ARQ_JOB_TIMEOUT_SECONDS: int = 60 * 60
    ARQ_RESULT_TTL_SECONDS: int = 60 * 60
    JOB_ARTIFACT_STORAGE_DIRECTORY: str = str(
        REPO_ROOT
        / "backend"
        / "app"
        / "infrastructure"
        / "job_artifact_storage"
        / "files"
    )

    CODEX_JOB_MODEL: str = "gpt-5.5"
    CODEX_JOB_REASONING_EFFORT: Literal["low", "medium", "high", "xhigh"] = "low"
    CODEX_JOB_WORKING_DIRECTORY: str = str(
        REPO_ROOT / "backend" / "app" / "infrastructure" / "arq" / ".codex_work_dir"
    )
    CODEX_JOB_SANDBOX_MODE: Literal[
        "read-only",
        "workspace-write",
        "danger-full-access",
    ] = "workspace-write"
    CODEX_JOB_APPROVAL_POLICY: Literal[
        "untrusted",
        "on-request",
        "never",
    ] = "never"
    CODEX_JOB_IDLE_TIMEOUT_SECONDS: int = 60
    CODEX_JOB_MAX_TURNS: int = 10
    CODEX_JOB_EVENTS_STREAM: str = "codex-job-events"
    CODEX_JOB_EVENTS_STREAM_MAXLEN: int = 10_000
    CODEX_CLI_PATH: str = "codex"
    CODEX_DEVICE_LOGIN_START_TIMEOUT_SECONDS: float = 10.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """Return all allowed CORS origins."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Build the SQLAlchemy database URI."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        """Default sender display name to the project name."""
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        """Return whether SMTP is configured enough to send email."""
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """Warn locally and fail outside local for unchanged default secrets."""
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """Check deployment-sensitive defaults."""
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD",
            self.FIRST_SUPERUSER_PASSWORD,
        )
        return self


settings = Settings()
