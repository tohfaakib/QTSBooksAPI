from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "dev"
    TIMEZONE: str = "Asia/Dhaka"
    API_KEY: str = "test-api-key"  # will change later or from env
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "qtsbook"
    RATE_LIMIT: str = "100/hour"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FK_", extra="ignore")

@lru_cache
def get_settings() -> "Settings":
    return Settings()

settings = get_settings()
