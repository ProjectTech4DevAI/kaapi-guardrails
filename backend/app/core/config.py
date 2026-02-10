import os
from pathlib import Path
from typing import Any, ClassVar, Literal
import warnings

from pydantic import (
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "testing"
    AUTH_TOKEN: str
    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    GUARDRAILS_HUB_API_KEY: str | None = None
    CORE_DIR: ClassVar[Path] = Path(__file__).resolve().parent

    SLUR_LIST_FILENAME: ClassVar[str] = "curated_slurlist_hi_en.csv"

    SLUR_LIST_FILEPATH: ClassVar[Path] = (
        CORE_DIR / "validators" / "utils" / "files" / SLUR_LIST_FILENAME
    )

    GENDER_BIAS_LIST_FILEPATH: ClassVar[Path] = (
        CORE_DIR / "validators" / "utils" / "files" / "gender_assumption_bias_words.csv"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "testing":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        return self


def get_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development")

    ROOT_DIR = Path(__file__).resolve().parents[3]

    env_files = {
        "testing": ROOT_DIR / ".env.test",
        "staging": ROOT_DIR / ".env.test",
        "development": ROOT_DIR / ".env",
        "production": ROOT_DIR / ".env",
    }

    env_file = env_files.get(environment)

    return Settings(_env_file=env_file)


settings = get_settings()
