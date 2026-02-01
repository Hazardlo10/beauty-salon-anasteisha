"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str = "local-development-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Telegram (опционально для локальной разработки)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_CHAT_ID: Optional[str] = None
    TELEGRAM_DEV_CHAT_ID: Optional[str] = None

    # SMS (опционально)
    SMS_API_KEY: Optional[str] = None
    SMS_SENDER: str = "Beauty"

    # Payment (опционально)
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None

    # Application
    SITE_URL: str = "http://localhost:8000"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PHONE: str = "+79000000000"

    # Booking Settings
    SLOT_DURATION_MINUTES: int = 30
    BOOKING_DAYS_AHEAD: int = 30
    REMINDER_HOURS_BEFORE: int = 24

    # Development
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    class Config:
        # Путь к .env относительно корня проекта
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (с кешированием)"""
    return Settings()
