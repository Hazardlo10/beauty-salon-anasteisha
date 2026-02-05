"""
Модель персонального расписания мастера
"""
from sqlalchemy import Column, Integer, Time, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class MasterAvailability(Base):
    """
    Персональное расписание мастера по дням недели.
    Определяет, когда мастер может принимать клиентов
    (в рамках общего расписания салона).
    """

    __tablename__ = "master_availability"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False, unique=True)  # 0=Пн, 6=Вс
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_available = Column(Boolean, default=True)  # Работает ли мастер в этот день
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        status = "✅" if self.is_available else "❌"
        return f"<MasterAvailability {days[self.day_of_week]} {self.start_time}-{self.end_time} {status}>"


# Дефолтное расписание мастера (совпадает с салоном)
DEFAULT_MASTER_AVAILABILITY = [
    {"day_of_week": 0, "start_time": "10:00", "end_time": "20:00", "is_available": True},  # Пн
    {"day_of_week": 1, "start_time": "10:00", "end_time": "20:00", "is_available": True},  # Вт
    {"day_of_week": 2, "start_time": "10:00", "end_time": "20:00", "is_available": True},  # Ср
    {"day_of_week": 3, "start_time": "10:00", "end_time": "20:00", "is_available": True},  # Чт
    {"day_of_week": 4, "start_time": "10:00", "end_time": "20:00", "is_available": True},  # Пт
    {"day_of_week": 5, "start_time": "10:00", "end_time": "18:00", "is_available": True},  # Сб
    {"day_of_week": 6, "start_time": "10:00", "end_time": "18:00", "is_available": True},  # Вс
]
