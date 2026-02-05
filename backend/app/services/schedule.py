"""
Сервис для работы с расписанием и слотами
"""
from datetime import date, time, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from ..models.work_schedule import WorkSchedule, DEFAULT_SCHEDULE
from ..models.blocked_slot import BlockedSlot
from ..models.appointment import Appointment
from ..models.master_availability import MasterAvailability, DEFAULT_MASTER_AVAILABILITY
from ..config import get_settings

settings = get_settings()


class ScheduleService:
    """Сервис управления расписанием"""

    def __init__(self, db: Session):
        self.db = db
        self.slot_duration = settings.SLOT_DURATION_MINUTES

    def get_working_hours(self, target_date: date) -> Optional[dict]:
        """
        Получить рабочие часы на конкретную дату
        Возвращает dict с start_time, end_time, is_working_day или None
        """
        # Python: понедельник = 0, воскресенье = 6
        day_of_week = target_date.weekday()

        schedule = self.db.query(WorkSchedule).filter(
            WorkSchedule.day_of_week == day_of_week
        ).first()

        if schedule:
            return {
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "is_working_day": schedule.is_working_day
            }

        # Если расписание не найдено в БД - используем дефолтное
        for default in DEFAULT_SCHEDULE:
            if default["day_of_week"] == day_of_week:
                return {
                    "start_time": datetime.strptime(default["start_time"], "%H:%M").time(),
                    "end_time": datetime.strptime(default["end_time"], "%H:%M").time(),
                    "is_working_day": default["is_working_day"]
                }

        return None

    def get_master_availability(self, target_date: date) -> Optional[dict]:
        """
        Получить доступность мастера на конкретную дату
        Возвращает dict с start_time, end_time, is_available или None
        """
        day_of_week = target_date.weekday()

        availability = self.db.query(MasterAvailability).filter(
            MasterAvailability.day_of_week == day_of_week
        ).first()

        if availability:
            return {
                "start_time": availability.start_time,
                "end_time": availability.end_time,
                "is_available": availability.is_available
            }

        # Если расписание мастера не найдено - используем дефолтное
        for default in DEFAULT_MASTER_AVAILABILITY:
            if default["day_of_week"] == day_of_week:
                return {
                    "start_time": datetime.strptime(default["start_time"], "%H:%M").time(),
                    "end_time": datetime.strptime(default["end_time"], "%H:%M").time(),
                    "is_available": default["is_available"]
                }

        return None

    def get_effective_working_hours(self, target_date: date) -> Optional[dict]:
        """
        Получить эффективные рабочие часы - пересечение расписания салона
        и доступности мастера
        """
        salon_hours = self.get_working_hours(target_date)
        if not salon_hours or not salon_hours["is_working_day"]:
            return None

        master_hours = self.get_master_availability(target_date)
        if not master_hours or not master_hours["is_available"]:
            return None

        # Пересечение интервалов: берём максимум из начал и минимум из концов
        effective_start = max(salon_hours["start_time"], master_hours["start_time"])
        effective_end = min(salon_hours["end_time"], master_hours["end_time"])

        # Проверяем, что интервал валидный
        if effective_start >= effective_end:
            return None

        return {
            "start_time": effective_start,
            "end_time": effective_end,
            "is_working_day": True
        }

    def generate_time_slots(self, start: time, end: time, duration_minutes: int = None) -> List[time]:
        """
        Генерация всех временных слотов между start и end
        """
        if duration_minutes is None:
            duration_minutes = self.slot_duration

        slots = []
        current = datetime.combine(date.today(), start)
        end_dt = datetime.combine(date.today(), end)

        while current + timedelta(minutes=duration_minutes) <= end_dt:
            slots.append(current.time())
            current += timedelta(minutes=duration_minutes)

        return slots

    def get_booked_slots(self, target_date: date) -> List[dict]:
        """
        Получить все занятые слоты (записи) на дату
        Возвращает список dict с time и duration
        """
        appointments = self.db.query(Appointment).filter(
            Appointment.appointment_date == target_date,
            Appointment.status.in_(["pending", "confirmed"])
        ).all()

        return [
            {
                "time": apt.appointment_time,
                "duration": apt.duration_minutes
            }
            for apt in appointments
        ]

    def get_blocked_slots(self, target_date: date) -> List[dict]:
        """
        Получить заблокированные слоты на дату
        """
        blocked = self.db.query(BlockedSlot).filter(
            BlockedSlot.slot_date == target_date
        ).all()

        return [
            {
                "time": slot.slot_time,
                "duration": slot.duration_minutes
            }
            for slot in blocked
        ]

    def is_slot_available(
        self,
        target_date: date,
        slot_time: time,
        service_duration: int = None
    ) -> bool:
        """
        Проверить, доступен ли конкретный слот
        Учитывает длительность услуги
        """
        if service_duration is None:
            service_duration = self.slot_duration

        # Проверяем эффективные рабочие часы (пересечение салона и мастера)
        working = self.get_effective_working_hours(target_date)
        if not working or not working["is_working_day"]:
            return False

        # Слот должен быть в рабочих часах
        if slot_time < working["start_time"]:
            return False

        # Окончание услуги не должно выходить за рабочие часы
        slot_end = datetime.combine(date.today(), slot_time) + timedelta(minutes=service_duration)
        working_end = datetime.combine(date.today(), working["end_time"])
        if slot_end > working_end:
            return False

        # Проверяем, не в прошлом ли слот
        now = datetime.now()
        slot_datetime = datetime.combine(target_date, slot_time)
        if slot_datetime <= now:
            return False

        # Проверяем пересечение с записями
        booked = self.get_booked_slots(target_date)
        blocked = self.get_blocked_slots(target_date)

        all_busy = booked + blocked

        for busy in all_busy:
            busy_start = datetime.combine(date.today(), busy["time"])
            busy_end = busy_start + timedelta(minutes=busy["duration"])

            slot_start = datetime.combine(date.today(), slot_time)
            slot_end = slot_start + timedelta(minutes=service_duration)

            # Проверяем пересечение интервалов
            if slot_start < busy_end and slot_end > busy_start:
                return False

        return True

    def get_available_slots(
        self,
        target_date: date,
        service_duration: int = None
    ) -> List[time]:
        """
        Получить все доступные слоты на дату
        Учитывает длительность услуги
        """
        if service_duration is None:
            service_duration = self.slot_duration

        # Получаем эффективные рабочие часы (пересечение салона и мастера)
        working = self.get_effective_working_hours(target_date)
        if not working or not working["is_working_day"]:
            return []

        # Генерируем все слоты
        all_slots = self.generate_time_slots(
            working["start_time"],
            working["end_time"],
            self.slot_duration  # Шаг всегда 30 минут
        )

        # Фильтруем доступные
        available = [
            slot for slot in all_slots
            if self.is_slot_available(target_date, slot, service_duration)
        ]

        return available

    def get_available_dates(self, days_ahead: int = None) -> List[date]:
        """
        Получить список дат с доступными слотами
        """
        if days_ahead is None:
            days_ahead = settings.BOOKING_DAYS_AHEAD

        available_dates = []
        today = date.today()

        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            slots = self.get_available_slots(check_date)
            if slots:
                available_dates.append(check_date)

        return available_dates

    def block_slot(
        self,
        target_date: date,
        slot_time: time,
        duration: int = None,
        reason: str = None
    ) -> BlockedSlot:
        """
        Заблокировать слот
        """
        if duration is None:
            duration = self.slot_duration

        blocked = BlockedSlot(
            slot_date=target_date,
            slot_time=slot_time,
            duration_minutes=duration,
            reason=reason
        )
        self.db.add(blocked)
        self.db.commit()
        self.db.refresh(blocked)
        return blocked

    def unblock_slot(self, target_date: date, slot_time: time) -> bool:
        """
        Разблокировать слот
        """
        blocked = self.db.query(BlockedSlot).filter(
            BlockedSlot.slot_date == target_date,
            BlockedSlot.slot_time == slot_time
        ).first()

        if blocked:
            self.db.delete(blocked)
            self.db.commit()
            return True
        return False

    def init_default_schedule(self):
        """
        Инициализировать расписание по умолчанию
        """
        existing = self.db.query(WorkSchedule).count()
        if existing > 0:
            return  # Расписание уже есть

        for day_data in DEFAULT_SCHEDULE:
            schedule = WorkSchedule(
                day_of_week=day_data["day_of_week"],
                start_time=datetime.strptime(day_data["start_time"], "%H:%M").time(),
                end_time=datetime.strptime(day_data["end_time"], "%H:%M").time(),
                is_working_day=day_data["is_working_day"]
            )
            self.db.add(schedule)

        self.db.commit()

    def init_master_availability(self):
        """
        Инициализировать расписание мастера по умолчанию
        """
        existing = self.db.query(MasterAvailability).count()
        if existing > 0:
            return  # Расписание мастера уже есть

        for day_data in DEFAULT_MASTER_AVAILABILITY:
            availability = MasterAvailability(
                day_of_week=day_data["day_of_week"],
                start_time=datetime.strptime(day_data["start_time"], "%H:%M").time(),
                end_time=datetime.strptime(day_data["end_time"], "%H:%M").time(),
                is_available=day_data["is_available"]
            )
            self.db.add(availability)

        self.db.commit()

    def set_master_availability(
        self,
        day_of_week: int,
        start_time: time,
        end_time: time,
        is_available: bool = True
    ) -> MasterAvailability:
        """
        Установить доступность мастера на конкретный день недели
        """
        availability = self.db.query(MasterAvailability).filter(
            MasterAvailability.day_of_week == day_of_week
        ).first()

        if availability:
            availability.start_time = start_time
            availability.end_time = end_time
            availability.is_available = is_available
        else:
            availability = MasterAvailability(
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                is_available=is_available
            )
            self.db.add(availability)

        self.db.commit()
        self.db.refresh(availability)
        return availability

    def toggle_master_day(self, day_of_week: int, is_available: bool) -> MasterAvailability:
        """
        Включить/выключить рабочий день мастера
        """
        availability = self.db.query(MasterAvailability).filter(
            MasterAvailability.day_of_week == day_of_week
        ).first()

        if availability:
            availability.is_available = is_available
        else:
            # Создаём с дефолтными часами
            for default in DEFAULT_MASTER_AVAILABILITY:
                if default["day_of_week"] == day_of_week:
                    availability = MasterAvailability(
                        day_of_week=day_of_week,
                        start_time=datetime.strptime(default["start_time"], "%H:%M").time(),
                        end_time=datetime.strptime(default["end_time"], "%H:%M").time(),
                        is_available=is_available
                    )
                    self.db.add(availability)
                    break

        self.db.commit()
        self.db.refresh(availability)
        return availability

    def get_master_week_schedule(self) -> List[dict]:
        """
        Получить полное недельное расписание мастера
        """
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        result = []

        for day_num in range(7):
            availability = self.db.query(MasterAvailability).filter(
                MasterAvailability.day_of_week == day_num
            ).first()

            if availability:
                result.append({
                    "day_of_week": day_num,
                    "day_name": days[day_num],
                    "start_time": availability.start_time.strftime("%H:%M"),
                    "end_time": availability.end_time.strftime("%H:%M"),
                    "is_available": availability.is_available
                })
            else:
                # Используем дефолтное
                for default in DEFAULT_MASTER_AVAILABILITY:
                    if default["day_of_week"] == day_num:
                        result.append({
                            "day_of_week": day_num,
                            "day_name": days[day_num],
                            "start_time": default["start_time"],
                            "end_time": default["end_time"],
                            "is_available": default["is_available"]
                        })
                        break

        return result
