"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OS-DBX Backend"
    environment: str = "development"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "os_dbx"
    # Keep local development self-contained; set EVENT_STORAGE=mysql when
    # the MySQL schema is available and OS events should be durable.
    event_storage: str = "memory"
    dbms_collection_interval_seconds: int = 5

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
