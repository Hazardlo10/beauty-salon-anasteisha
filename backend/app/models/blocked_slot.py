"""
Модель заблокированных временных слотов
"""
from sqlalchemy import Column, Integer, Date, Time, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from ..database import Base


class BlockedSlot(Base):
    """Заблокированные слоты (обед, выходные, личное время)"""

    __tablename__ = "blocked_slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_date = Column(Date, nullable=False, index=True)
    slot_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30)
    reason = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('slot_date', 'slot_time', name='unique_blocked_slot'),
    )

    def __repr__(self):
        return f"<BlockedSlot {self.slot_date} {self.slot_time} - {self.reason}>"
