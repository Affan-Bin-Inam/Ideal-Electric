from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str = Field(min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    turnstile_secret_key: str = Field(min_length=1)

    model_config = SettingsConfigDict(env_file=".env")
    
    media_dir: str = "media"
    media_url_prefix: str = "/media"
    max_image_bytes: int = 10 * 1024 * 1024
    max_document_bytes: int = 20 * 1024 * 1024
    max_image_pixels: int = 40_000_000


settings = Settings()