"""
Модель рабочего расписания
"""
from sqlalchemy import Column, Integer, Time, Boolean
from ..database import Base


class WorkSchedule(Base):
    """Расписание работы по дням недели"""

    __tablename__ = "work_schedule"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False, unique=True)  # 0=Пн, 6=Вс
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_working_day = Column(Boolean, default=True)

    def __repr__(self):
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"<WorkSchedule {days[self.day_of_week]} {self.start_time}-{self.end_time}>"


# Дефолтное расписание для инициализации
DEFAULT_SCHEDULE = [
    {"day_of_week": 0, "start_time": "10:00", "end_time": "20:00", "is_working_day": True},  # Пн
    {"day_of_week": 1, "start_time": "10:00", "end_time": "20:00", "is_working_day": True},  # Вт
    {"day_of_week": 2, "start_time": "10:00", "end_time": "20:00", "is_working_day": True},  # Ср
    {"day_of_week": 3, "start_time": "10:00", "end_time": "20:00", "is_working_day": True},  # Чт
    {"day_of_week": 4, "start_time": "10:00", "end_time": "20:00", "is_working_day": True},  # Пт
    {"day_of_week": 5, "start_time": "10:00", "end_time": "18:00", "is_working_day": True},  # Сб
    {"day_of_week": 6, "start_time": "10:00", "end_time": "18:00", "is_working_day": True},  # Вс
]
