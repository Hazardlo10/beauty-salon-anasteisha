"""
Модель услуги
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class Service(Base):
    """Услуга косметологического кабинета"""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    category = Column(String(50), nullable=True)
    image_url = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<Service {self.name} ({self.price}₽)>"
