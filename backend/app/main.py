"""
Главный файл FastAPI приложения
Beauty Salon Booking System - Anasteisha
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, date, timedelta
import httpx

from .config import get_settings
from .database import engine, Base, SessionLocal
from .models.booking_lead import BookingLead
from .models.review import Review
from .models.problem_report import ProblemReport
from .models.appointment import Appointment
from .models.client import Client
from .models.service import Service
from .routes.appointments import router as appointments_router
from .services.schedule import ScheduleService
from .services.notifications import notify_client_booking_confirmed, notify_client_booking_cancelled

settings = get_settings()


class BookingRequest(BaseModel):
    name: str
    phone: str
    email: str = ""
    service: str
    message: str = ""


class ReviewRequest(BaseModel):
    name: str
    phone: str = ""
    rating: int
    text: str
    service: str = ""


class ProblemReportRequest(BaseModel):
    name: str = ""
    email: str = ""
    problem_type: str
    description: str
    page_url: str = ""


async def send_telegram_to_salon(text: str) -> bool:
    """Отправка сообщения СПЕЦИАЛИСТУ (записи, отзывы)"""
    # Сначала пробуем бот специалиста, если не настроен - используем основной
    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_SALON_CHAT_ID or settings.TELEGRAM_ADMIN_CHAT_ID

    if not bot_token or not chat_id:
        print("Telegram для специалиста не настроен")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram (специалист): {e}")
        return False


async def send_telegram_to_developer(text: str) -> bool:
    """Отправка сообщения РАЗРАБОТЧИКУ (проблемы с сайтом)"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_ADMIN_CHAT_ID:
        print("Telegram для разработчика не настроен")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": settings.TELEGRAM_ADMIN_CHAT_ID, "text": text, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram (разработчик): {e}")
        return False


# Алиас для обратной совместимости
async def send_telegram_message(text: str) -> bool:
    return await send_telegram_to_salon(text)

# Создание таблиц в БД
Base.metadata.create_all(bind=engine)

# Инициализация расписания по умолчанию
def init_default_schedule():
    db = SessionLocal()
    try:
        schedule_service = ScheduleService(db)
        schedule_service.init_default_schedule()
    finally:
        db.close()

init_default_schedule()

# FastAPI приложение
app = FastAPI(
    title="Anasteisha - Beauty Salon API",
    description="API для системы онлайн-записи",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.SITE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(appointments_router)

# Статические файлы
frontend_path = Path(__file__).parent.parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# Fallback endpoint для услуг (если роутер не загрузился)
@app.get("/api/services")
async def get_services_fallback():
    """Получить список услуг (fallback)"""
    db = SessionLocal()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()
        if services:
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "duration_minutes": s.duration_minutes,
                    "price": float(s.price),
                    "category": s.category,
                    "image_url": s.image_url
                }
                for s in services
            ]
    except Exception as e:
        print(f"Ошибка загрузки услуг: {e}")
    finally:
        db.close()

    # Fallback - хардкод услуги если БД пустая
    return [
        {"id": 1, "name": "Атравматическая чистка лица", "price": 2500, "duration_minutes": 60, "category": "Лицо", "description": None, "image_url": None},
        {"id": 2, "name": "Лифтинг-омоложение лица", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": None, "image_url": None},
        {"id": 3, "name": "Липосомальное обновление кожи", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": None, "image_url": None},
        {"id": 4, "name": "Ферментотерапия лица", "price": 2800, "duration_minutes": 75, "category": "Лицо", "description": None, "image_url": None},
        {"id": 5, "name": "Безынъекционный ботокс лица", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": None, "image_url": None},
        {"id": 6, "name": "Атравматическая чистка спины", "price": 4500, "duration_minutes": 90, "category": "Комплекс", "description": None, "image_url": None},
        {"id": 7, "name": "Лифтинг шеи и декольте", "price": 3500, "duration_minutes": 75, "category": "Комплекс", "description": None, "image_url": None},
        {"id": 8, "name": "Обновление лица и декольте", "price": 3500, "duration_minutes": 120, "category": "Комплекс", "description": None, "image_url": None},
        {"id": 9, "name": "Ботокс лица и шеи", "price": 3800, "duration_minutes": 105, "category": "Комплекс", "description": None, "image_url": None},
    ]

@app.get("/")
async def read_root():
    return FileResponse(str(frontend_path.parent / "index.html"))


@app.get("/my-bookings.html")
async def my_bookings_page():
    return FileResponse(str(frontend_path.parent / "my-bookings.html"))


@app.post("/api/booking")
async def create_booking(booking: BookingRequest):
    """Создание заявки на запись"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Сохраняем в базу данных
    db = SessionLocal()
    try:
        db_lead = BookingLead(
            name=booking.name,
            phone=booking.phone,
            email=booking.email or None,
            service=booking.service,
            message=booking.message or None,
            status="new"
        )
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        lead_id = db_lead.id
    except Exception as e:
        db.rollback()
        print(f"Ошибка сохранения в БД: {e}")
        lead_id = None
    finally:
        db.close()

    # Формируем сообщение для Telegram
    message = f"""📅 <b>НОВАЯ ЗАПИСЬ</b> 📅
━━━━━━━━━━━━━━━━━━

👤 <b>Клиент:</b> {booking.name}
📞 <b>Телефон:</b> {booking.phone}
📧 <b>Email:</b> {booking.email or "—"}
💆 <b>Услуга:</b> {booking.service}
💬 <b>Сообщение:</b> {booking.message or "—"}

🕐 {now} • ID #{lead_id or "N/A"}
"""

    # Отправляем СПЕЦИАЛИСТУ
    sent = await send_telegram_to_salon(message)

    # Обновляем статус отправки в БД
    if sent and lead_id:
        db = SessionLocal()
        try:
            db_lead = db.query(BookingLead).filter(BookingLead.id == lead_id).first()
            if db_lead:
                db_lead.telegram_sent = True
                db.commit()
        finally:
            db.close()

    return {"success": True, "message": "Заявка успешно отправлена", "id": lead_id}


@app.post("/api/review")
async def create_review(review: ReviewRequest):
    """Создание отзыва"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Валидация рейтинга
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Рейтинг должен быть от 1 до 5")

    # Сохраняем в базу данных
    db = SessionLocal()
    try:
        db_review = Review(
            name=review.name,
            phone=review.phone or None,
            rating=review.rating,
            text=review.text,
            service=review.service or None,
            is_published=False
        )
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        review_id = db_review.id
    except Exception as e:
        db.rollback()
        print(f"Ошибка сохранения отзыва: {e}")
        review_id = None
    finally:
        db.close()

    # Формируем звёздочки для рейтинга
    stars = "⭐" * review.rating + "☆" * (5 - review.rating)

    # Формируем сообщение для Telegram
    message = f"""💬 <b>НОВЫЙ ОТЗЫВ</b> 💬
━━━━━━━━━━━━━━━━━━

{stars}  <b>({review.rating}/5)</b>

👤 <b>Клиент:</b> {review.name}
📞 <b>Телефон:</b> {review.phone or "—"}
💆 <b>Услуга:</b> {review.service or "—"}

📝 <b>Текст:</b>
<i>"{review.text}"</i>

🕐 {now} • ID #{review_id or "N/A"}
"""

    # Отправляем СПЕЦИАЛИСТУ
    sent = await send_telegram_to_salon(message)

    if sent and review_id:
        db = SessionLocal()
        try:
            db_review = db.query(Review).filter(Review.id == review_id).first()
            if db_review:
                db_review.telegram_sent = True
                db.commit()
        finally:
            db.close()

    return {"success": True, "message": "Спасибо за отзыв!", "id": review_id}


@app.post("/api/problem")
async def create_problem_report(report: ProblemReportRequest):
    """Сообщение о проблеме"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Сохраняем в базу данных
    db = SessionLocal()
    try:
        db_report = ProblemReport(
            name=report.name or None,
            email=report.email or None,
            problem_type=report.problem_type,
            description=report.description,
            page_url=report.page_url or None,
            status="new"
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        report_id = db_report.id
    except Exception as e:
        db.rollback()
        print(f"Ошибка сохранения отчёта: {e}")
        report_id = None
    finally:
        db.close()

    # Типы проблем с эмодзи
    problem_types = {
        "bug": ("🐛", "ОШИБКА НА САЙТЕ"),
        "suggestion": ("💡", "ПРЕДЛОЖЕНИЕ"),
        "question": ("❓", "ВОПРОС"),
        "other": ("📌", "ДРУГОЕ")
    }
    emoji, type_text = problem_types.get(report.problem_type, ("📌", report.problem_type.upper()))

    # Формируем сообщение для Telegram (для разработчика - выделено особо)
    message = f"""🚨🚨🚨 <b>ДЛЯ РАЗРАБОТЧИКА</b> 🚨🚨🚨
══════════════════════════

{emoji} <b>{type_text}</b> {emoji}

👤 <b>От кого:</b> {report.name or "Аноним"}
📧 <b>Email:</b> {report.email or "—"}
🔗 <b>Страница:</b> {report.page_url or "—"}

━━━━━━━━━━━━━━━━━━
📋 <b>ОПИСАНИЕ:</b>
{report.description}
━━━━━━━━━━━━━━━━━━

🕐 {now} • ID #{report_id or "N/A"}
══════════════════════════
"""

    # Отправляем РАЗРАБОТЧИКУ
    sent = await send_telegram_to_developer(message)

    if sent and report_id:
        db = SessionLocal()
        try:
            db_report = db.query(ProblemReport).filter(ProblemReport.id == report_id).first()
            if db_report:
                db_report.telegram_sent = True
                db.commit()
        finally:
            db.close()

    return {"success": True, "message": "Сообщение отправлено!", "id": report_id}


# ==================== Telegram Webhook ====================

async def answer_callback_query(callback_id: str, text: str) -> bool:
    """Ответ на callback query (убирает часики)"""
    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    data = {"callback_query_id": callback_id, "text": text}

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data)
            return True
    except Exception:
        return False


async def edit_message_reply_markup(chat_id: int, message_id: int, reply_markup: dict = None) -> bool:
    """Изменить кнопки сообщения"""
    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup"
    data = {"chat_id": chat_id, "message_id": message_id}
    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data)
            return True
    except Exception:
        return False


async def send_message_with_keyboard(chat_id: int, text: str, keyboard: dict = None) -> bool:
    """Отправить сообщение с клавиатурой"""
    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data)
            return True
    except Exception:
        return False


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """Webhook для обработки callback от Telegram бота"""
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    # Обработка callback_query (нажатие на inline-кнопку)
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback.get("data", "")
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]

        # apt_confirm_123 или apt_reject_123
        if callback_data.startswith("apt_confirm_"):
            apt_id = int(callback_data.replace("apt_confirm_", ""))
            db = SessionLocal()
            try:
                appointment = db.query(Appointment).filter(Appointment.id == apt_id).first()
                if appointment:
                    appointment.status = "confirmed"
                    db.commit()

                    client = db.query(Client).filter(Client.id == appointment.client_id).first()
                    service = db.query(Service).filter(Service.id == appointment.service_id).first()

                    await answer_callback_query(callback_id, "✅ Запись подтверждена!")
                    await edit_message_reply_markup(chat_id, message_id, None)

                    # Отправляем сообщение об успехе специалисту
                    apt_date_str = appointment.appointment_date.strftime("%d.%m.%Y")
                    apt_time_str = appointment.appointment_time.strftime("%H:%M")
                    await send_message_with_keyboard(
                        chat_id,
                        f"✅ <b>ЗАПИСЬ #{apt_id} ПОДТВЕРЖДЕНА</b>\n\n"
                        f"👤 {client.name if client else 'Клиент'}\n"
                        f"💆 {service.name if service else 'Услуга'}\n"
                        f"📆 {apt_date_str} в {apt_time_str}",
                        None
                    )

                    # Уведомляем клиента о подтверждении
                    await notify_client_booking_confirmed(
                        client_email=client.email if client else None,
                        client_telegram_id=client.telegram_id if client else None,
                        client_name=client.name if client else "Клиент",
                        client_phone=client.phone if client else "",
                        service_name=service.name if service else "Услуга",
                        appointment_date=appointment.appointment_date,
                        appointment_time=apt_time_str,
                        appointment_id=apt_id
                    )
                else:
                    await answer_callback_query(callback_id, "❌ Запись не найдена")
            finally:
                db.close()

        elif callback_data.startswith("apt_reject_"):
            apt_id = int(callback_data.replace("apt_reject_", ""))
            db = SessionLocal()
            try:
                appointment = db.query(Appointment).filter(Appointment.id == apt_id).first()
                if appointment:
                    appointment.status = "cancelled"
                    db.commit()

                    client = db.query(Client).filter(Client.id == appointment.client_id).first()

                    service = db.query(Service).filter(Service.id == appointment.service_id).first()

                    await answer_callback_query(callback_id, "❌ Запись отклонена")
                    await edit_message_reply_markup(chat_id, message_id, None)

                    apt_time_str = appointment.appointment_time.strftime("%H:%M")
                    await send_message_with_keyboard(
                        chat_id,
                        f"❌ <b>ЗАПИСЬ #{apt_id} ОТКЛОНЕНА</b>\n\n"
                        f"👤 {client.name if client else 'Клиент'}\n"
                        f"📞 {client.phone if client else ''}\n\n"
                        f"<i>Не забудьте связаться с клиентом!</i>",
                        None
                    )

                    # Уведомляем клиента об отмене
                    await notify_client_booking_cancelled(
                        client_email=client.email if client else None,
                        client_telegram_id=client.telegram_id if client else None,
                        client_name=client.name if client else "Клиент",
                        client_phone=client.phone if client else "",
                        service_name=service.name if service else "Услуга",
                        appointment_date=appointment.appointment_date,
                        appointment_time=apt_time_str
                    )
                else:
                    await answer_callback_query(callback_id, "❌ Запись не найдена")
            finally:
                db.close()

    # Обработка команд
    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        if text == "/today":
            # Записи на сегодня
            db = SessionLocal()
            try:
                today = date.today()
                appointments = db.query(Appointment).filter(
                    Appointment.appointment_date == today,
                    Appointment.status.in_(["pending", "confirmed"])
                ).order_by(Appointment.appointment_time).all()

                if appointments:
                    lines = [f"📅 <b>ЗАПИСИ НА СЕГОДНЯ ({today.strftime('%d.%m.%Y')})</b>\n"]
                    for apt in appointments:
                        client = db.query(Client).filter(Client.id == apt.client_id).first()
                        service = db.query(Service).filter(Service.id == apt.service_id).first()
                        status_emoji = "✅" if apt.status == "confirmed" else "⏳"
                        lines.append(
                            f"{status_emoji} <b>{apt.appointment_time.strftime('%H:%M')}</b> - "
                            f"{client.name if client else '?'} ({service.name if service else '?'})"
                        )
                    await send_telegram_to_salon("\n".join(lines))
                else:
                    await send_telegram_to_salon("📅 На сегодня записей нет")
            finally:
                db.close()

        elif text == "/week":
            # Записи на неделю
            db = SessionLocal()
            try:
                today = date.today()
                week_end = today + timedelta(days=7)
                appointments = db.query(Appointment).filter(
                    Appointment.appointment_date >= today,
                    Appointment.appointment_date <= week_end,
                    Appointment.status.in_(["pending", "confirmed"])
                ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

                if appointments:
                    lines = [f"📅 <b>ЗАПИСИ НА НЕДЕЛЮ</b>\n"]
                    current_date = None
                    for apt in appointments:
                        if apt.appointment_date != current_date:
                            current_date = apt.appointment_date
                            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                            day_name = day_names[current_date.weekday()]
                            lines.append(f"\n<b>{current_date.strftime('%d.%m')} ({day_name})</b>")

                        client = db.query(Client).filter(Client.id == apt.client_id).first()
                        service = db.query(Service).filter(Service.id == apt.service_id).first()
                        status_emoji = "✅" if apt.status == "confirmed" else "⏳"
                        lines.append(
                            f"  {status_emoji} {apt.appointment_time.strftime('%H:%M')} - "
                            f"{client.name if client else '?'}"
                        )
                    await send_telegram_to_salon("\n".join(lines))
                else:
                    await send_telegram_to_salon("📅 На ближайшую неделю записей нет")
            finally:
                db.close()

        elif text.startswith("/block"):
            # /block 2024-01-15 14:00 [причина]
            parts = text.split(" ", 3)
            if len(parts) >= 3:
                try:
                    block_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
                    block_time = datetime.strptime(parts[2], "%H:%M").time()
                    reason = parts[3] if len(parts) > 3 else "Заблокировано специалистом"

                    schedule_service = ScheduleService(SessionLocal())
                    schedule_service.block_slot(block_date, block_time, reason=reason)

                    await send_telegram_to_salon(
                        f"🔒 <b>СЛОТ ЗАБЛОКИРОВАН</b>\n\n"
                        f"📆 {block_date.strftime('%d.%m.%Y')} в {block_time.strftime('%H:%M')}\n"
                        f"💬 {reason}"
                    )
                except ValueError:
                    await send_telegram_to_salon(
                        "❌ Неверный формат.\n"
                        "Используйте: /block YYYY-MM-DD HH:MM [причина]\n"
                        "Пример: /block 2024-01-15 14:00 Обед"
                    )
            else:
                await send_telegram_to_salon(
                    "ℹ️ <b>Блокировка слота</b>\n\n"
                    "Формат: /block YYYY-MM-DD HH:MM [причина]\n"
                    "Пример: /block 2024-01-15 14:00 Обед"
                )

        elif text == "/help":
            await send_telegram_to_salon(
                "📋 <b>КОМАНДЫ БОТА</b>\n\n"
                "/today - записи на сегодня\n"
                "/week - записи на неделю\n"
                "/block ДАТА ВРЕМЯ - заблокировать слот\n"
                "/help - эта справка"
            )

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=settings.DEBUG)
