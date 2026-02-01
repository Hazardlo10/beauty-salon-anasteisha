"""
Модель клиента
"""
from sqlalchemy import Column, Integer, String, BigInteger, Date, Text, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class Client(Base):
    """Клиент косметологического кабинета"""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Client {self.name} ({self.phone})>"
