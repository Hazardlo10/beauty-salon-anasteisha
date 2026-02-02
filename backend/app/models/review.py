"""
Модель отзыва клиента
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from ..database import Base


class Review(Base):
    """Отзыв клиента"""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    text = Column(Text, nullable=False)
    service = Column(String(200), nullable=True)
    is_published = Column(Boolean, default=False)  # Модерация перед публикацией
    telegram_sent = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<Review {self.name} - {self.rating} stars>"
