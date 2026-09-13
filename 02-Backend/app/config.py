import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379"
    DATABASE_URL: str = "sqlite:///astrovox.db"
    
    MODEL_ALIASES: dict = {
        "cheap": "gpt-4o-mini-2024-07-18",
        "medium": "gpt-4o-2024-08-06",
        "premium": "gpt-4-turbo-2024-04-09",
    }
    
    DAILY_BUDGET_USD: float = 10.0
    PER_USER_DAILY_CAP_USD: float = 1.0
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production-32-chars-min")
    JWT_ALGORITHM: str = "HS256"
    
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
