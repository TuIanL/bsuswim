from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
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
    pdf_browser_executable_path: str | None = None

    # AI report interpretation is opt-in. A configured API key alone never
    # enables external data transfer.
    ai_interpretation_enabled: bool = False
    ai_interpretation_auto_generate: bool = False
    ai_interpretation_provider: str = "qwen"
    ai_interpretation_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ai_interpretation_model: str = "qwen-plus"
    ai_interpretation_api_key: SecretStr | None = None
    ai_interpretation_timeout_seconds: float = 120.0
    ai_interpretation_max_retries: int = 2
    ai_interpretation_temperature: float = 0.0
    ai_interpretation_max_output_tokens: int | None = None
    ai_interpretation_thinking_enabled: bool = True
    # `qwen-plus` is configured as text-only until a visual Qwen model has
    # been explicitly verified by deployment. These flags prevent accidental
    # image transfer merely because an API key is present.
    ai_interpretation_visual_enabled: bool = False
    ai_interpretation_model_supports_vision: bool = False
    ai_interpretation_model_supports_structured_output: bool = True
    ai_interpretation_max_evidence_images: int = 9
    ai_interpretation_max_evidence_bytes: int = 6_000_000
    ai_interpretation_max_evidence_image_pixels: int = 2_000_000
    ai_interpretation_max_curve_points: int = 48
    ai_interpretation_max_input_chars: int = 24000
    ai_interpretation_max_estimated_cost_usd: float = 0.02
    ai_interpretation_input_cost_per_million_tokens: float = 0.14
    ai_interpretation_output_cost_per_million_tokens: float = 0.28
    ai_interpretation_max_knowledge_items: int = 6
    ai_interpretation_debug_retention: bool = False
    ai_interpretation_stale_after_seconds: int = 600
    ai_interpretation_rate_limit_per_hour: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def ai_interpretation_configured(self) -> bool:
        has_credentials = self.ai_interpretation_provider == "fake" or bool(
            self.ai_interpretation_api_key
            and self.ai_interpretation_api_key.get_secret_value()
        )
        return bool(
            self.ai_interpretation_enabled
            and self.ai_interpretation_provider
            and self.ai_interpretation_model
            and has_credentials
        )

    @property
    def ai_interpretation_visual_configured(self) -> bool:
        return bool(
            self.ai_interpretation_configured
            and self.ai_interpretation_visual_enabled
            and self.ai_interpretation_model_supports_vision
            and self.ai_interpretation_model_supports_structured_output
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
