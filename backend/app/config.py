"""
Central application configuration, loaded from environment variables (and a
local .env file in development). Nothing secret is hardcoded here — see
.env.example for the variables this expects.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # lru_cache means the .env file is only read once per process, and the
    # same Settings instance is reused everywhere via the get_settings() dependency.
    return Settings()
