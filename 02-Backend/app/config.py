import os
from typing import Optional


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///astrovox.db")
    
    MODEL_ALIASES: dict = {
        "cheap": "gpt-4o-mini-2024-07-18",
        "medium": "gpt-4o-2024-08-06",
        "premium": "gpt-4-turbo-2024-04-09",
    }
    
    DAILY_BUDGET_USD: float = float(os.getenv("DAILY_BUDGET_USD", "10.0"))
    PER_USER_DAILY_CAP_USD: float = float(os.getenv("PER_USER_DAILY_CAP_USD", "1.0"))
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")


settings = Settings()
