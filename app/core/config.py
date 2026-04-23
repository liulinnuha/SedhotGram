from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "Instagram Downloader API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]

    # MongoDB
    MONGODB_URL: str = "mongodb://mongo:27017"
    MONGODB_DB_NAME: str = "instagram_downloader"

    # Redis (Queue)
    REDIS_URL: str = "redis://redis:6379"
    QUEUE_NAME: str = "instagram_download_queue"
    QUEUE_MAX_RETRIES: int = 3
    WORKER_CONCURRENCY: int = 4

    # InstaLoader
    INSTALOADER_SESSION_FILE: str = "/tmp/instaloader_session"
    INSTAGRAM_USERNAME: str = ""
    INSTAGRAM_PASSWORD: str = ""
    DOWNLOAD_DIR: str = "/tmp/downloads"
    # Storage
    MEDIA_BASE_URL: str = "http://localhost:8000/media"


settings = Settings()
