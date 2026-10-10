"""Application settings loaded from environment / .env file."""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./mill.db"
    secret_key: str = "dev-secret-change-me"
    session_hours: int = 8
    cors_origins: list[str] = ["http://localhost:3000"]
    cookie_secure: bool = False
    serverless: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
