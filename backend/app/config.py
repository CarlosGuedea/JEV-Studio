"""Application configuration.

All secrets come from environment variables (see .env.example).
Nothing sensitive is ever stored inside workflow JSON.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Jev Studio Backend"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./jevstudio.db"

    # CORS (dev default; override via env in production)
    cors_origins: str = "http://localhost:3000,http://localhost:7100,http://127.0.0.1:3000"

    # ── Jev (TypeSafe System One) ─────────────────────────────────────
    # Official API: POST {jev_base_url}/v1/systemone  body {state, questions, model}
    jev_base_url: str = "https://api.typesafe.ai"
    jev_model: str = "jev-latest"
    # API key is read ONLY from the environment, never from workflows.
    typesafe_api_key: str | None = None
    jev_api_key: str | None = None
    jev_timeout_seconds: float = 60.0

    # ── LLM providers (OpenAI-compatible) ─────────────────────────────
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 60.0
    llm_max_response_bytes: int = 2_000_000

    # ── HTTP Request node ─────────────────────────────────────────────
    http_timeout_seconds: float = 30.0
    http_max_response_bytes: int = 2_000_000
    # Comma-separated allowlist; empty means allow all http(s) hosts.
    http_allowed_hosts: str = ""

    # ── Python node ───────────────────────────────────────────────────
    python_max_input_bytes: int = 256_000

    # ── Engine ────────────────────────────────────────────────────────
    engine_max_steps: int = 200
    engine_step_timeout_seconds: float = 120.0

    # ── Workflow scheduler ──────────────────────────────────────────
    scheduler_poll_seconds: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_jev_api_key(self) -> str | None:
        return self.jev_api_key or self.typesafe_api_key

    @property
    def http_allowed_host_list(self) -> list[str]:
        return [h.strip().lower() for h in self.http_allowed_hosts.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
