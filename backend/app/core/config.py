from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "智泳云枢业务后端"
    api_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://swim:swim@127.0.0.1:3306/swim_analysis?charset=utf8mb4"
    upload_dir: Path = Path("uploads")
    model_service_url: str = "http://127.0.0.1:8100"
    model_service_timeout_seconds: float = 120.0
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
