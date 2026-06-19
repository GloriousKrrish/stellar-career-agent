"""
Centralized application configuration.
All settings are loaded from environment variables / .env file.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Stellar Career Agent API"
    app_version: str = "2.0.0"
    app_env: str = "development"
    debug: bool = True

    # Security
    secret_key: str = "stellar-career-agent-super-secret-key-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:8080"

    # AI Keys
    gemini_api_key: str = ""
    firecrawl_api_key: str = ""

    # Logging
    log_level: str = "INFO"

    # Upload
    upload_dir: str = "uploads"
    max_file_size_mb: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
