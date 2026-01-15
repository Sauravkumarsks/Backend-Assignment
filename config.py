import os
from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str
    webhook_secret: str
    log_level: str = "INFO"


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
    webhook_secret = os.getenv("WEBHOOK_SECRET", "")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    return Settings(database_url=database_url, webhook_secret=webhook_secret, log_level=log_level)
