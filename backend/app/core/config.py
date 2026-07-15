from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "智泳云枢业务后端"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://swim:swim@localhost:5432/swim_analysis"
    upload_dir: Path = Path("uploads")
    model_service_url: str = "http://127.0.0.1:8100"
    model_service_timeout_seconds: float = 120.0
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    frontend_base_url: str = "http://localhost:5174"
    pdf_render_base_url: str = "http://localhost:5174"
    backend_public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
