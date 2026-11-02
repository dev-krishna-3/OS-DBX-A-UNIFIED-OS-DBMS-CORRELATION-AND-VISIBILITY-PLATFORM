"""Application settings."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OS-DBX Backend"
    environment: str = "development"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "osdbx_app"
    mysql_password: str = ""
    mysql_database: str = "os_dbx"
    # Keep local development self-contained; set EVENT_STORAGE=mysql when
    # the MySQL schema is available and OS events should be durable.
    event_storage: str = "memory"
    cors_origins: list[str] = Field(default_factory=list)
    allow_public_registration: bool = True
    dbms_collection_interval_seconds: int = 5
    os_watch_paths: list[str] = ["."]

    # SMTP Email Notification Settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_database_credentials(self):
        if self.environment.lower() in {"production", "prod"}:
            if self.mysql_user.lower() == "root" or not self.mysql_password:
                raise ValueError("Production requires a non-root MySQL user and MYSQL_PASSWORD.")
            if self.event_storage.strip().lower() != "mysql":
                raise ValueError("Production requires EVENT_STORAGE=mysql.")
        return self


settings = Settings()
