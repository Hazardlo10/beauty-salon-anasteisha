"""
Модель записи на прием
"""
from sqlalchemy import Column, Integer, ForeignKey, Date, Time, String, Numeric, Text, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class Appointment(Base):
    """Запись на прием"""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    status = Column(String(20), default="pending")  # pending, confirmed, completed, cancelled, no_show
    duration_minutes = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(20), default="unpaid")  # unpaid, paid, refunded
    payment_method = Column(String(20), nullable=True)  # cash, card, online
    notes = Column(Text, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Appointment {self.appointment_date} {self.appointment_time} (Status: {self.status})>"
