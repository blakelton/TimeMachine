"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="TIMEMACHINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    env: Literal["development", "production"] = "development"
    debug: bool = False

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Database
    db_path: Path = Field(default_factory=lambda: Path("./data/timemachine.db"))

    # Storage
    media_path: Path = Field(default_factory=lambda: Path("./data/media"))

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # Authentication (optional)
    auth_enabled: bool = False
    auth_username: str = "admin"
    auth_password: str | None = None

    # Encoder defaults
    default_resolution: str = "1920x1080"
    default_fps: int = 30
    default_bitrate: int = 4_000_000  # 4 Mbps
    h264_profile: Literal["baseline", "main", "high"] = "main"

    # Retention
    retention_days: int = 30
    retention_max_gb: float = 50.0

    # Resource limits
    min_memory_mb: int = 100
    min_disk_mb: int = 500

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def database_url(self) -> str:
        """SQLAlchemy database URL."""
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins based on environment."""
        if self.env == "development":
            return ["*"]
        return self.cors_origins

    def validate_auth(self) -> None:
        """Validate authentication configuration."""
        if self.auth_enabled and not self.auth_password:
            raise ValueError(
                "TIMEMACHINE_AUTH_PASSWORD is required when authentication is enabled"
            )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
