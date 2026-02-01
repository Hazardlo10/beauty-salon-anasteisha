"""
Модель уведомления
"""
from sqlalchemy import Column, Integer, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class Notification(Base):
    """Уведомление клиенту"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    notification_type = Column(String(20), nullable=False)  # telegram, sms, email
    message = Column(Text, nullable=False)
    sent_at = Column(TIMESTAMP, server_default=func.now())
    status = Column(String(20), default="sent")  # sent, failed, delivered

    def __repr__(self):
        return f"<Notification {self.notification_type} (Status: {self.status})>"
