"""Application settings."""

import json
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OS-DBX Backend"
    environment: str = "development"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "osdbx_app"
    mysql_password: str = ""
    mysql_database: str = "os_dbx"
    mysql_connect_timeout: int = 10
    mysql_pool_size: int = 4
    mysql_ssl_required: bool = False
    mysql_ssl_ca: str = ""
    mysql_ssl_ca_pem: str = ""
    auto_init_schema: bool = False
    # Keep local development self-contained; set EVENT_STORAGE=mysql when
    # the MySQL schema is available and OS events should be durable.
    event_storage: str = "memory"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    allow_public_registration: bool = True
    dbms_collection_interval_seconds: int = 5
    os_watch_paths: list[str] = ["."]

    # SMTP Email Notification Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "osdbx86@gmail.com"
    smtp_password: str = "udgtrcqcgiddvxes"
    smtp_from_email: str = "osdbx86@gmail.com"
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """Accept both JSON arrays and comma-separated origin strings from env vars."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                return [str(item).strip().rstrip("/") for item in parsed if str(item).strip()]
            return [part.strip().rstrip("/") for part in raw.split(",") if part.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip().rstrip("/") for item in value if str(item).strip()]
        return value

    @model_validator(mode="after")
    def require_production_database_credentials(self):
        if self.environment.lower() in {"production", "prod"}:
            if self.mysql_user.lower() == "root" or not self.mysql_password:
                raise ValueError("Production requires a non-root MySQL user and MYSQL_PASSWORD.")
            if self.event_storage.strip().lower() != "mysql":
                raise ValueError("Production requires EVENT_STORAGE=mysql.")
        return self


settings = Settings()
