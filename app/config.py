from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---------------------------------------------------------
    # ENVIRONMENT
    # ---------------------------------------------------------
    env: str = "prod"

    # ---------------------------------------------------------
    # REDIS (aiocache backend)
    # ---------------------------------------------------------

    # enable/disable caching in middleware
    enable_cache: bool = True

    redis_host: str = "redis" #"localhost" #(if backend runs in WSL)
    redis_port: int = 6379

    # Cache TTL for endpoint responses
    cache_ttl_seconds: int = 300

    # ---------------------------------------------------------
    # RATE LIMITING
    # ---------------------------------------------------------
    rate_limit_per_minute: int = 60

    # ---------------------------------------------------------
    # YFINANCE CONFIG 
    # ---------------------------------------------------------
    # Network
    yf_proxy: str | None = None
    yf_retries: int = 0

    # Debug
    yf_debug_hide_exceptions: bool = True
    yf_debug_logging: bool = True #False

    # Locale
    yf_locale_lang: str = "en-US"
    yf_locale_region: str = "US"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
