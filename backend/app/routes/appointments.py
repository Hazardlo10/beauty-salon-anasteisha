"""
API роутер для записей на прием
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date, time, datetime, timedelta
from typing import Optional, List
import httpx

from ..database import get_db
from ..models.client import Client
from ..models.service import Service
from ..models.appointment import Appointment
from ..services.schedule import ScheduleService
from ..services.notifications import (
    notify_client_booking_created,
    notify_client_booking_confirmed,
    notify_client_booking_cancelled,
    notify_client_booking_rescheduled
)
from ..config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api", tags=["appointments"])


# ==================== Pydantic Schemas ====================

class ServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    duration_minutes: int
    price: float
    category: Optional[str]
    image_url: Optional[str]

    class Config:
        from_attributes = True


class TimeSlotResponse(BaseModel):
    time: str  # "HH:MM"
    available: bool = True


class ScheduleResponse(BaseModel):
    date: str  # "YYYY-MM-DD"
    is_working_day: bool
    working_hours: Optional[dict] = None  # {"start": "10:00", "end": "20:00"}
    slots: List[TimeSlotResponse]


class AppointmentCreate(BaseModel):
    service_id: int
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    appointment_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM
    client_name: str = Field(..., min_length=2, max_length=100)
    client_phone: str = Field(..., min_length=10, max_length=20)
    client_email: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    service_name: str
    service_price: float
    appointment_date: str
    appointment_time: str
    status: str
    duration_minutes: int
    total_price: float
    created_at: str
    can_cancel: bool
    can_reschedule: bool


class AppointmentUpdate(BaseModel):
    new_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    new_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    status: Optional[str] = None  # cancelled


# ==================== Telegram Functions ====================

async def send_appointment_notification(
    appointment: Appointment,
    service: Service,
    client: Client,
    action: str = "new"
) -> bool:
    """Отправить уведомление о записи с inline-кнопками"""
    print(f"[TG] === НАЧАЛО ОТПРАВКИ УВЕДОМЛЕНИЯ ===", flush=True)

    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_SALON_CHAT_ID or settings.TELEGRAM_ADMIN_CHAT_ID

    print(f"[TG] SALON_BOT_TOKEN: {settings.TELEGRAM_SALON_BOT_TOKEN[:20] if settings.TELEGRAM_SALON_BOT_TOKEN else 'None'}...", flush=True)
    print(f"[TG] SALON_CHAT_ID: {settings.TELEGRAM_SALON_CHAT_ID}", flush=True)
    print(f"[TG] Итого: bot={bot_token[:20] if bot_token else 'None'}..., chat={chat_id}", flush=True)

    if not bot_token or not chat_id:
        print(f"[TG] ОШИБКА: bot_token или chat_id пустой!", flush=True)
        return False

    apt_date = appointment.appointment_date.strftime("%d.%m.%Y")
    apt_time = appointment.appointment_time.strftime("%H:%M")
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    if action == "new":
        emoji = "📅"
        title = "НОВАЯ ЗАПИСЬ"
        status_text = "Ожидает подтверждения"
    elif action == "cancelled":
        emoji = "❌"
        title = "ЗАПИСЬ ОТМЕНЕНА"
        status_text = "Отменено клиентом"
    elif action == "rescheduled":
        emoji = "🔄"
        title = "ЗАПИСЬ ПЕРЕНЕСЕНА"
        status_text = "Новое время"
    else:
        emoji = "📋"
        title = "ОБНОВЛЕНИЕ ЗАПИСИ"
        status_text = appointment.status

    message = f"""{emoji} <b>{title}</b> {emoji}
━━━━━━━━━━━━━━━━━━

👤 <b>Клиент:</b> {client.name}
📞 <b>Телефон:</b> {client.phone}
📧 <b>Email:</b> {client.email or "—"}

💆 <b>Услуга:</b> {service.name}
⏱ <b>Длительность:</b> {service.duration_minutes} мин
💰 <b>Стоимость:</b> {service.price}₽

📆 <b>Дата:</b> {apt_date}
🕐 <b>Время:</b> {apt_time}

📋 <b>Статус:</b> {status_text}
💬 <b>Заметка:</b> {appointment.notes or "—"}

🕐 {now} • ID #{appointment.id}"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Inline-кнопки только для новых записей
    keyboard = None
    if action == "new":
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Подтвердить", "callback_data": f"apt_confirm_{appointment.id}"},
                    {"text": "❌ Отклонить", "callback_data": f"apt_reject_{appointment.id}"}
                ]
            ]
        }

    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    if keyboard:
        data["reply_markup"] = keyboard

    try:
        async with httpx.AsyncClient() as http_client:
            # Отправка специалисту
            print(f"[TG] Отправка специалисту: bot={bot_token[:20]}..., chat={chat_id}")
            response = await http_client.post(url, json=data)
            print(f"[TG] Ответ специалисту: {response.status_code} - {response.text[:200]}")

            # Также отправка разработчику (без inline-кнопок)
            dev_bot_token = settings.TELEGRAM_BOT_TOKEN
            dev_chat_id = settings.TELEGRAM_DEV_CHAT_ID
            if dev_bot_token and dev_chat_id and dev_chat_id != chat_id:
                dev_url = f"https://api.telegram.org/bot{dev_bot_token}/sendMessage"
                dev_data = {
                    "chat_id": dev_chat_id,
                    "text": f"📋 <i>[Копия для разработчика]</i>\n\n{message}",
                    "parse_mode": "HTML"
                }
                dev_response = await http_client.post(dev_url, json=dev_data)
                print(f"[TG] Ответ разработчику: {dev_response.status_code}")

            return response.status_code == 200
    except Exception as e:
        print(f"[TG] Ошибка отправки в Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== API Endpoints ====================

@router.get("/services", response_model=List[ServiceResponse])
async def get_services(db: Session = Depends(get_db)):
    """Получить список активных услуг"""
    services = db.query(Service).filter(Service.is_active == True).all()
    return services


@router.get("/schedule/{date_str}", response_model=ScheduleResponse)
async def get_schedule(
    date_str: str,
    service_id: Optional[int] = Query(None, description="ID услуги для учёта длительности"),
    db: Session = Depends(get_db)
):
    """Получить расписание на дату с доступными слотами"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")

    # Проверка, что дата не в прошлом
    if target_date < date.today():
        raise HTTPException(status_code=400, detail="Нельзя записаться на прошедшую дату")

    # Проверка, что дата не слишком далеко
    max_date = date.today() + timedelta(days=settings.BOOKING_DAYS_AHEAD)
    if target_date > max_date:
        raise HTTPException(
            status_code=400,
            detail=f"Запись возможна максимум на {settings.BOOKING_DAYS_AHEAD} дней вперёд"
        )

    # Определяем длительность услуги
    service_duration = settings.SLOT_DURATION_MINUTES
    if service_id:
        service = db.query(Service).filter(Service.id == service_id).first()
        if service:
            service_duration = service.duration_minutes

    schedule_service = ScheduleService(db)
    working = schedule_service.get_working_hours(target_date)

    if not working or not working["is_working_day"]:
        return ScheduleResponse(
            date=date_str,
            is_working_day=False,
            working_hours=None,
            slots=[]
        )

    # Получаем доступные слоты
    available_slots = schedule_service.get_available_slots(target_date, service_duration)

    # Все возможные слоты
    all_slots = schedule_service.generate_time_slots(
        working["start_time"],
        working["end_time"]
    )

    slots = [
        TimeSlotResponse(
            time=slot.strftime("%H:%M"),
            available=slot in available_slots
        )
        for slot in all_slots
    ]

    return ScheduleResponse(
        date=date_str,
        is_working_day=True,
        working_hours={
            "start": working["start_time"].strftime("%H:%M"),
            "end": working["end_time"].strftime("%H:%M")
        },
        slots=slots
    )


@router.get("/schedule/dates/available", response_model=List[str])
async def get_available_dates(
    service_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Получить список дат с доступными слотами"""
    service_duration = settings.SLOT_DURATION_MINUTES
    if service_id:
        service = db.query(Service).filter(Service.id == service_id).first()
        if service:
            service_duration = service.duration_minutes

    schedule_service = ScheduleService(db)
    # Используем упрощённую проверку - только рабочие дни
    available = []
    today = date.today()

    for i in range(settings.BOOKING_DAYS_AHEAD):
        check_date = today + timedelta(days=i)
        working = schedule_service.get_working_hours(check_date)
        if working and working["is_working_day"]:
            slots = schedule_service.get_available_slots(check_date, service_duration)
            if slots:
                available.append(check_date.strftime("%Y-%m-%d"))

    return available


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    """Создать новую запись на прием"""
    # Валидация услуги
    service = db.query(Service).filter(Service.id == data.service_id, Service.is_active == True).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    # Парсинг даты и времени
    try:
        apt_date = datetime.strptime(data.appointment_date, "%Y-%m-%d").date()
        apt_time = datetime.strptime(data.appointment_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты или времени")

    # Проверка доступности слота
    schedule_service = ScheduleService(db)
    if not schedule_service.is_slot_available(apt_date, apt_time, service.duration_minutes):
        raise HTTPException(status_code=400, detail="Выбранное время недоступно")

    # Нормализация телефона
    phone = data.client_phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        elif phone.startswith("7"):
            phone = "+" + phone
        else:
            phone = "+7" + phone

    # Получаем или создаём клиента
    client = db.query(Client).filter(Client.phone == phone).first()
    if not client:
        client = Client(
            name=data.client_name,
            phone=phone,
            email=data.client_email
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    else:
        # Обновляем имя и email если изменились
        if data.client_name and data.client_name != client.name:
            client.name = data.client_name
        if data.client_email and data.client_email != client.email:
            client.email = data.client_email
        db.commit()

    # Проверка 1: клиент уже записан на это время
    existing_client = db.query(Appointment).filter(
        Appointment.client_id == client.id,
        Appointment.appointment_date == apt_date,
        Appointment.appointment_time == apt_time,
        Appointment.status.in_(["pending", "confirmed"])
    ).first()

    if existing_client:
        raise HTTPException(
            status_code=400,
            detail="У вас уже есть запись на это время. Проверьте раздел 'Мои записи'."
        )

    # Проверка 2: слот уже занят другим клиентом (главная проверка!)
    existing_slot = db.query(Appointment).filter(
        Appointment.appointment_date == apt_date,
        Appointment.appointment_time == apt_time,
        Appointment.status.in_(["pending", "confirmed"])
    ).first()

    if existing_slot:
        raise HTTPException(
            status_code=400,
            detail="Это время уже занято. Пожалуйста, выберите другое время."
        )

    # Создаём запись
    appointment = Appointment(
        client_id=client.id,
        service_id=service.id,
        appointment_date=apt_date,
        appointment_time=apt_time,
        status="pending",
        duration_minutes=service.duration_minutes,
        total_price=service.price,
        notes=data.notes
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Отправляем уведомление специалисту
    await send_appointment_notification(appointment, service, client, "new")

    # Отправляем уведомление клиенту (email/telegram или напоминание позвонить)
    await notify_client_booking_created(
        client_email=client.email,
        client_telegram_id=client.telegram_id,
        client_name=client.name,
        client_phone=client.phone,
        service_name=service.name,
        appointment_date=apt_date,
        appointment_time=apt_time.strftime("%H:%M"),
        price=float(service.price),
        appointment_id=appointment.id
    )

    # Определяем возможность отмены/переноса
    apt_datetime = datetime.combine(apt_date, apt_time)
    hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600

    return AppointmentResponse(
        id=appointment.id,
        service_name=service.name,
        service_price=float(service.price),
        appointment_date=apt_date.strftime("%Y-%m-%d"),
        appointment_time=apt_time.strftime("%H:%M"),
        status=appointment.status,
        duration_minutes=appointment.duration_minutes,
        total_price=float(appointment.total_price),
        created_at=appointment.created_at.strftime("%Y-%m-%d %H:%M"),
        can_cancel=hours_until >= 2,
        can_reschedule=hours_until >= 2
    )


@router.get("/appointments/my", response_model=List[AppointmentResponse])
async def get_my_appointments(
    phone: str = Query(..., min_length=10, description="Номер телефона"),
    db: Session = Depends(get_db)
):
    """Получить записи клиента по номеру телефона"""
    # Нормализация телефона
    phone_clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone_clean.startswith("+"):
        if phone_clean.startswith("8"):
            phone_clean = "+7" + phone_clean[1:]
        elif phone_clean.startswith("7"):
            phone_clean = "+" + phone_clean
        else:
            phone_clean = "+7" + phone_clean

    client = db.query(Client).filter(Client.phone == phone_clean).first()
    if not client:
        return []

    # Записи за последние 30 дней и на будущее
    thirty_days_ago = date.today() - timedelta(days=30)
    appointments = db.query(Appointment).filter(
        Appointment.client_id == client.id,
        Appointment.appointment_date >= thirty_days_ago
    ).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()

    result = []
    for apt in appointments:
        service = db.query(Service).filter(Service.id == apt.service_id).first()
        apt_datetime = datetime.combine(apt.appointment_date, apt.appointment_time)
        hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600

        # Можно отменить/перенести только pending/confirmed записи за 2+ часа
        can_modify = apt.status in ["pending", "confirmed"] and hours_until >= 2

        result.append(AppointmentResponse(
            id=apt.id,
            service_name=service.name if service else "Неизвестная услуга",
            service_price=float(service.price) if service else 0,
            appointment_date=apt.appointment_date.strftime("%Y-%m-%d"),
            appointment_time=apt.appointment_time.strftime("%H:%M"),
            status=apt.status,
            duration_minutes=apt.duration_minutes,
            total_price=float(apt.total_price),
            created_at=apt.created_at.strftime("%Y-%m-%d %H:%M"),
            can_cancel=can_modify,
            can_reschedule=can_modify
        ))

    return result


@router.patch("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    phone: str = Query(..., min_length=10, description="Номер телефона для верификации"),
    db: Session = Depends(get_db)
):
    """Изменить или отменить запись"""
    # Нормализация телефона
    phone_clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone_clean.startswith("+"):
        if phone_clean.startswith("8"):
            phone_clean = "+7" + phone_clean[1:]
        elif phone_clean.startswith("7"):
            phone_clean = "+" + phone_clean
        else:
            phone_clean = "+7" + phone_clean

    # Находим клиента
    client = db.query(Client).filter(Client.phone == phone_clean).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Находим запись
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.client_id == client.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    # Проверяем, можно ли изменить
    apt_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
    hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600

    if hours_until < 2:
        raise HTTPException(
            status_code=400,
            detail="Изменение возможно минимум за 2 часа до записи"
        )

    if appointment.status not in ["pending", "confirmed"]:
        raise HTTPException(status_code=400, detail="Эту запись нельзя изменить")

    service = db.query(Service).filter(Service.id == appointment.service_id).first()

    # Отмена
    if data.status == "cancelled":
        appointment.status = "cancelled"
        db.commit()
        await send_appointment_notification(appointment, service, client, "cancelled")

        # Уведомляем клиента об отмене
        await notify_client_booking_cancelled(
            client_email=client.email,
            client_telegram_id=client.telegram_id,
            client_name=client.name,
            client_phone=client.phone,
            service_name=service.name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time.strftime("%H:%M")
        )

        return {"success": True, "message": "Запись отменена"}

    # Перенос
    if data.new_date or data.new_time:
        # Сохраняем старые значения для уведомления
        old_date = appointment.appointment_date
        old_time = appointment.appointment_time

        new_date = old_date
        new_time = old_time

        if data.new_date:
            new_date = datetime.strptime(data.new_date, "%Y-%m-%d").date()
        if data.new_time:
            new_time = datetime.strptime(data.new_time, "%H:%M").time()

        # Проверяем доступность нового слота
        schedule_service = ScheduleService(db)
        if not schedule_service.is_slot_available(new_date, new_time, service.duration_minutes):
            raise HTTPException(status_code=400, detail="Новое время недоступно")

        appointment.appointment_date = new_date
        appointment.appointment_time = new_time
        db.commit()

        await send_appointment_notification(appointment, service, client, "rescheduled")

        # Уведомляем клиента о переносе
        await notify_client_booking_rescheduled(
            client_email=client.email,
            client_telegram_id=client.telegram_id,
            client_name=client.name,
            client_phone=client.phone,
            service_name=service.name,
            old_date=old_date,
            old_time=old_time.strftime("%H:%M"),
            new_date=new_date,
            new_time=new_time.strftime("%H:%M"),
            appointment_id=appointment.id
        )

        return {
            "success": True,
            "message": "Запись перенесена",
            "new_date": new_date.strftime("%Y-%m-%d"),
            "new_time": new_time.strftime("%H:%M")
        }

    return {"success": True, "message": "Запись обновлена"}


# ==================== ЗАЯВКИ НА ЗАПИСЬ (упрощённая форма) ====================

class BookingRequestCreate(BaseModel):
    """Заявка на запись (без выбора конкретного времени)"""
    service_id: Optional[int] = None
    service_name: str
    client_name: str
    client_phone: str
    time_preference: str = "any"  # morning, afternoon, evening, any
    comment: Optional[str] = None


@router.post("/booking-requests")
async def create_booking_request(
    request: BookingRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Создать заявку на запись.
    Мастер получит уведомление и сам свяжется с клиентом.
    """
    # Названия предпочтений времени
    time_pref_labels = {
        "morning": "Утро (9:00-12:00)",
        "afternoon": "День (12:00-17:00)",
        "evening": "Вечер (17:00-21:00)",
        "any": "Любое время"
    }

    time_pref_text = time_pref_labels.get(request.time_preference, request.time_preference)

    # Формируем сообщение для мастера
    message = f"""📋 <b>НОВАЯ ЗАЯВКА С САЙТА!</b>

👤 <b>Клиент:</b> {request.client_name}
📱 <b>Телефон:</b> {request.client_phone}

💆 <b>Услуга:</b> {request.service_name}
🕐 <b>Предпочтительное время:</b> {time_pref_text}"""

    if request.comment:
        message += f"\n\n💬 <b>Комментарий:</b> {request.comment}"

    message += "\n\n<i>Свяжитесь с клиентом для согласования времени!</i>"

    # Отправляем уведомление мастеру
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    if bot_token and chat_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    },
                    timeout=10.0
                )
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")

    # Также отправляем разработчику (если настроен)
    dev_chat_id = settings.TELEGRAM_DEV_CHAT_ID
    if bot_token and dev_chat_id and dev_chat_id != chat_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": dev_chat_id,
                        "text": message + f"\n\n_Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
                        "parse_mode": "HTML"
                    },
                    timeout=10.0
                )
        except Exception:
            pass

    return {
        "success": True,
        "message": "Заявка отправлена",
        "id": int(datetime.now().timestamp())
    }


# ==================== ЗАЯВКИ НА КУРСЫ ====================

class CourseOrderCreate(BaseModel):
    name: str
    contact: str  # Telegram или телефон
    course: str
    price: str


@router.post("/course-order")
async def create_course_order(order: CourseOrderCreate):
    """Заявка на покупку гайда — уведомление мастеру в Telegram"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    message = f"""📚 <b>ЗАЯВКА НА ГАЙД!</b>

👤 <b>Имя:</b> {order.name}
📱 <b>Контакт:</b> {order.contact}

📖 <b>Гайд:</b> {order.course}
💰 <b>Стоимость:</b> {order.price} ₽

🕐 {now}

<i>Свяжитесь с клиентом, пришлите ссылку на оплату и PDF после получения!</i>"""

    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    if bot_token and chat_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                    timeout=10.0
                )
        except Exception as e:
            print(f"[course-order] Ошибка отправки в Telegram: {e}")

    return {"success": True}
