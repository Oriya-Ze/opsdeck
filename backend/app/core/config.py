import json
from enum import Enum
from functools import cached_property
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    DISABLED = "disabled"
    LOCAL = "local"
    COGNITO = "cognito"


class StorageType(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Same codebase for every environment — only env values change between
    local Docker Compose, HomeLab, and AWS/EKS deployments.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    AUTH_MODE: AuthMode = AuthMode.DISABLED

    DATABASE_URL: str = "postgresql://opsdeck:opsdeck@postgres:5432/opsdeck"
    API_V1_PREFIX: str = "/api"
    APP_NAME: str = "OpsDeck"
    APP_VERSION: str = "0.1.0"
    # Comma-separated origins or JSON array string — see cors_origin_list
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    ENCRYPTION_KEY: str = "opsdeck-dev-key-change-in-production-32b="

    STORAGE_TYPE: StorageType = StorageType.LOCAL
    S3_BUCKET: str | None = None
    S3_REGION: str | None = None

    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_FILE_SD_DIR: str = "/app/prometheus/file_sd"
    PROMETHEUS_INTERNAL_URL: str = "http://prometheus:9090"
    PROMETHEUS_URL: str = "http://localhost:9090"
    GRAFANA_URL: str = "http://localhost:3001"
    GRAFANA_EMBED_URL: str = (
        "http://localhost:3001/d/opsdeck-overview/opsdeck-overview"
        "?orgId=1&theme=dark&kiosk"
    )

    @cached_property
    def cors_origin_list(self) -> list[str]:
        stripped = self.CORS_ORIGINS.strip().strip("'\"")
        if stripped.startswith("["):
            return json.loads(stripped)
        return [item.strip() for item in stripped.split(",") if item.strip()]

    @field_validator("AUTH_MODE", mode="before")
    @classmethod
    def parse_auth_mode(cls, value: Any) -> AuthMode:
        if isinstance(value, str):
            return AuthMode(value.lower())
        return value

    @field_validator("STORAGE_TYPE", mode="before")
    @classmethod
    def parse_storage_type(cls, value: Any) -> StorageType:
        if isinstance(value, str):
            return StorageType(value.lower())
        return value


settings = Settings()
