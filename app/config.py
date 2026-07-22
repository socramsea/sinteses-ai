"""Configuração central. Toda credencial é server-side e nunca vai pra log."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # infra
    redis_url: str = "redis://redis:6379/0"
    env: str = "production"
    log_level: str = "INFO"

    # anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_enable_prompt_cache: bool = True

    # fal.ai — slug nunca chumbado, vem de config
    fal_key: str = ""
    fal_model_i2v: str = ""
    fal_model_t2v: str = ""

    # spaces
    spaces_key: str = ""
    spaces_secret: str = ""
    spaces_region: str = "nyc3"
    spaces_bucket: str = "sintese-media"
    spaces_endpoint: str = ""

    # custo
    job_budget_brl_max: float = 200.0
    job_max_retries: int = 2
    job_max_scenes: int = 12
    provider_poll_interval_s: int = 8
    provider_poll_timeout_s: int = 900

    # compliance
    ai_disclosure_label: str = "Cenas recriadas por IA · imagens ilustrativas"
    require_sources: bool = True
    allow_photoreal_real_event: bool = False

    def safe_dump(self) -> dict:
        """Versão sem segredos, pra logar com segurança."""
        secret = {"anthropic_api_key", "fal_key", "spaces_key", "spaces_secret"}
        return {k: ("***" if k in secret and v else v) for k, v in self.model_dump().items()}


settings = Settings()
