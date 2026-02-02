"""
Модель заявки с сайта (лид)
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from ..database import Base


class BookingLead(Base):
    """Заявка на запись с сайта"""

    __tablename__ = "booking_leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    service = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="new")  # new, contacted, confirmed, cancelled
    telegram_sent = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<BookingLead {self.name} - {self.service} ({self.status})>"
