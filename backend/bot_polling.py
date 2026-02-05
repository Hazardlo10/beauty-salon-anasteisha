"""
Telegram Bot Polling для локальной разработки

Запуск:
  python bot_polling.py           - бот специалиста (SALON)
  python bot_polling.py --dev     - бот разработчика (DEV) с теми же правами
"""
import sys
import asyncio
import re
import httpx
from datetime import date, timedelta, datetime, time as dt_time
from app.config import get_settings
from app.database import SessionLocal
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.service import Service
from app.models.review import Review
from app.services.notifications import notify_client_booking_confirmed, notify_client_booking_cancelled

settings = get_settings()

# Выбор бота по параметру запуска
IS_DEV_BOT = "--dev" in sys.argv
if IS_DEV_BOT:
    BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
    BOT_NAME = "РАЗРАБОТЧИКА"
else:
    BOT_TOKEN = settings.TELEGRAM_SALON_BOT_TOKEN
    BOT_NAME = "СПЕЦИАЛИСТА"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Хранилище состояний диалогов для интерактивных команд
# chat_id -> {"step": "...", "data": {...}}
conversations = {}


def normalize_phone(phone: str) -> str | None:
    """
    Проверяет и нормализует номер телефона.
    Возвращает номер в формате +79XXXXXXXXX или None если некорректный.
    """
    # Убираем всё кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Убираем + и работаем с цифрами
    digits = cleaned.replace('+', '')

    # Проверяем длину
    if len(digits) == 11:
        # Российский номер: 89XXXXXXXXX или 79XXXXXXXXX
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        if digits.startswith('7'):
            return '+' + digits
    elif len(digits) == 10:
        # Без кода страны: 9XXXXXXXXX
        if digits.startswith('9'):
            return '+7' + digits

    return None


async def get_updates(offset=None):
    """Получить обновления от Telegram"""
    url = f"{API_URL}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=35)
        return response.json()


async def answer_callback(callback_id: str, text: str):
    """Ответить на callback"""
    url = f"{API_URL}/answerCallbackQuery"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"callback_query_id": callback_id, "text": text})


async def send_message(chat_id: int, text: str):
    """Отправить сообщение"""
    url = f"{API_URL}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


async def send_message_with_keyboard(chat_id: int, text: str, keyboard: dict):
    """Отправить сообщение с inline клавиатурой"""
    url = f"{API_URL}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        })


async def process_callback(callback):
    """Обработать callback от кнопки"""
    callback_id = callback["id"]
    callback_data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]

    print(f"[BOT] Получен callback: {callback_data}")

    db = SessionLocal()
    try:
        if callback_data.startswith("apt_confirm_"):
            apt_id = int(callback_data.replace("apt_confirm_", ""))
            appointment = db.query(Appointment).filter(Appointment.id == apt_id).first()

            if appointment:
                appointment.status = "confirmed"
                db.commit()

                client = db.query(Client).filter(Client.id == appointment.client_id).first()
                service = db.query(Service).filter(Service.id == appointment.service_id).first()

                await answer_callback(callback_id, "✅ Запись подтверждена!")
                await send_message(chat_id, f"✅ Запись #{apt_id} подтверждена!\n\nКлиент: {client.name}\nТелефон: {client.phone}")

                # Уведомить клиента
                if client and service:
                    await notify_client_booking_confirmed(
                        client_email=client.email,
                        client_telegram_id=client.telegram_id,
                        client_name=client.name,
                        client_phone=client.phone,
                        service_name=service.name,
                        appointment_date=appointment.appointment_date,
                        appointment_time=appointment.appointment_time.strftime("%H:%M"),
                        appointment_id=appointment.id
                    )

                print(f"[BOT] Запись #{apt_id} подтверждена")
            else:
                await answer_callback(callback_id, "❌ Запись не найдена")

        elif callback_data.startswith("apt_reject_"):
            apt_id = int(callback_data.replace("apt_reject_", ""))
            appointment = db.query(Appointment).filter(Appointment.id == apt_id).first()

            if appointment:
                appointment.status = "cancelled"
                db.commit()

                client = db.query(Client).filter(Client.id == appointment.client_id).first()
                service = db.query(Service).filter(Service.id == appointment.service_id).first()

                await answer_callback(callback_id, "❌ Запись отклонена")
                await send_message(chat_id, f"❌ Запись #{apt_id} отклонена\n\nКлиент: {client.name}\nТелефон: {client.phone}")

                # Уведомить клиента
                if client and service:
                    await notify_client_booking_cancelled(
                        client_email=client.email,
                        client_telegram_id=client.telegram_id,
                        client_name=client.name,
                        client_phone=client.phone,
                        service_name=service.name,
                        appointment_date=appointment.appointment_date,
                        appointment_time=appointment.appointment_time.strftime("%H:%M")
                    )

                print(f"[BOT] Запись #{apt_id} отклонена")
            else:
                await answer_callback(callback_id, "❌ Запись не найдена")

        # Обработка отзывов
        elif callback_data.startswith("review_approve_"):
            review_id = int(callback_data.replace("review_approve_", ""))
            review = db.query(Review).filter(Review.id == review_id).first()

            if review:
                review.is_published = True
                db.commit()
                await answer_callback(callback_id, "✅ Отзыв опубликован!")
                text_preview = f"{review.text[:100]}..." if len(review.text) > 100 else review.text
                await send_message(chat_id, f"✅ <b>Отзыв #{review_id} опубликован!</b>\n\n👤 {review.name}\n⭐ {review.rating}/5\n💬 <i>\"{text_preview}\"</i>")
                print(f"[BOT] Отзыв #{review_id} опубликован")
            else:
                await answer_callback(callback_id, "❌ Отзыв не найден")

        elif callback_data.startswith("review_reject_"):
            review_id = int(callback_data.replace("review_reject_", ""))
            review = db.query(Review).filter(Review.id == review_id).first()

            if review:
                db.delete(review)
                db.commit()
                await answer_callback(callback_id, "🗑 Отзыв удалён")
                await send_message(chat_id, f"🗑 <b>Отзыв #{review_id} отклонён и удалён.</b>")
                print(f"[BOT] Отзыв #{review_id} удалён")
            else:
                await answer_callback(callback_id, "❌ Отзыв не найден")

        # ===== Интерактивная запись: выбор услуги =====
        elif callback_data.startswith("add_service_"):
            if chat_id not in conversations:
                await answer_callback(callback_id, "❌ Сессия истекла. Начните заново: /add")
                return

            service_id = int(callback_data.replace("add_service_", ""))
            service = db.query(Service).filter(Service.id == service_id).first()

            if service:
                conversations[chat_id]["data"]["service_id"] = service_id
                conversations[chat_id]["data"]["service_name"] = service.name
                conversations[chat_id]["data"]["duration"] = service.duration_minutes
                conversations[chat_id]["data"]["price"] = service.price
                conversations[chat_id]["step"] = "date"

                await answer_callback(callback_id, f"✅ {service.name}")

                # Показываем доступные даты (7 дней вперёд)
                buttons = []
                day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                for i in range(7):
                    d = date.today() + timedelta(days=i)
                    day_name = day_names[d.weekday()]
                    label = "Сегодня" if i == 0 else ("Завтра" if i == 1 else f"{day_name}, {d.strftime('%d.%m')}")
                    buttons.append([{"text": label, "callback_data": f"add_date_{d.isoformat()}"}])

                keyboard = {"inline_keyboard": buttons}
                await send_message_with_keyboard(chat_id,
                    f"✅ Услуга: <b>{service.name}</b>\n\n"
                    "Шаг 4/5: Выберите <b>дату</b>:",
                    keyboard
                )
            else:
                await answer_callback(callback_id, "❌ Услуга не найдена")

        # ===== Интерактивная запись: выбор даты =====
        elif callback_data.startswith("add_date_"):
            if chat_id not in conversations:
                await answer_callback(callback_id, "❌ Сессия истекла. Начните заново: /add")
                return

            date_str = callback_data.replace("add_date_", "")
            selected_date = date.fromisoformat(date_str)
            conversations[chat_id]["data"]["date"] = selected_date
            conversations[chat_id]["step"] = "time"

            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_name = day_names[selected_date.weekday()]

            await answer_callback(callback_id, f"✅ {day_name}, {selected_date.strftime('%d.%m')}")

            # Получаем свободные слоты
            is_weekend = selected_date.weekday() >= 5
            work_start = dt_time(10, 0)
            work_end = dt_time(18, 0) if is_weekend else dt_time(20, 0)
            slot_duration = 30

            # Находим занятые слоты
            appointments = db.query(Appointment).filter(
                Appointment.appointment_date == selected_date,
                Appointment.status.in_(["pending", "confirmed"])
            ).all()

            booked_times = set()
            for apt in appointments:
                apt_start = datetime.combine(selected_date, apt.appointment_time)
                apt_end = apt_start + timedelta(minutes=apt.duration_minutes or 60)
                current = apt_start
                while current < apt_end:
                    booked_times.add(current.time())
                    current += timedelta(minutes=slot_duration)

            # Генерируем свободные слоты
            free_slots = []
            current_time = work_start
            while current_time < work_end:
                if current_time not in booked_times:
                    free_slots.append(current_time)
                current_dt = datetime.combine(selected_date, current_time)
                current_dt += timedelta(minutes=slot_duration)
                current_time = current_dt.time()

            if not free_slots:
                await send_message(chat_id, "❌ На эту дату нет свободных слотов. Выберите другую дату.")
                # Показываем даты снова
                buttons = []
                for i in range(7):
                    d = date.today() + timedelta(days=i)
                    dn = day_names[d.weekday()]
                    label = "Сегодня" if i == 0 else ("Завтра" if i == 1 else f"{dn}, {d.strftime('%d.%m')}")
                    buttons.append([{"text": label, "callback_data": f"add_date_{d.isoformat()}"}])
                keyboard = {"inline_keyboard": buttons}
                await send_message_with_keyboard(chat_id, "Выберите другую дату:", keyboard)
            else:
                # Показываем слоты по 4 в ряд
                buttons = []
                row = []
                for slot in free_slots:
                    row.append({"text": slot.strftime('%H:%M'), "callback_data": f"add_time_{slot.strftime('%H:%M')}"})
                    if len(row) == 4:
                        buttons.append(row)
                        row = []
                if row:
                    buttons.append(row)

                keyboard = {"inline_keyboard": buttons}
                await send_message_with_keyboard(chat_id,
                    f"✅ Дата: <b>{day_name}, {selected_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"Шаг 5/5: Выберите <b>время</b> ({len(free_slots)} свободных слотов):",
                    keyboard
                )

        # ===== Интерактивная запись: выбор времени и создание записи =====
        elif callback_data.startswith("add_time_"):
            if chat_id not in conversations:
                await answer_callback(callback_id, "❌ Сессия истекла. Начните заново: /add")
                return

            time_str = callback_data.replace("add_time_", "")
            selected_time = datetime.strptime(time_str, "%H:%M").time()

            conv_data = conversations[chat_id]["data"]

            await answer_callback(callback_id, f"✅ {time_str}")

            # Создаём или находим клиента
            client = db.query(Client).filter(Client.phone == conv_data["phone"]).first()
            if not client:
                client = Client(
                    name=conv_data["name"],
                    phone=conv_data["phone"]
                )
                db.add(client)
                db.commit()
                db.refresh(client)

            # Создаём запись
            appointment = Appointment(
                client_id=client.id,
                service_id=conv_data["service_id"],
                appointment_date=conv_data["date"],
                appointment_time=selected_time,
                duration_minutes=conv_data["duration"],
                total_price=conv_data["price"],
                status="confirmed"
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)

            # Удаляем состояние диалога
            del conversations[chat_id]

            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_name = day_names[conv_data["date"].weekday()]

            await send_message(chat_id,
                f"✅ <b>Запись создана!</b>\n\n"
                f"🆔 ID: {appointment.id}\n"
                f"👤 Клиент: {conv_data['name']}\n"
                f"📱 Телефон: {conv_data['phone']}\n"
                f"💅 Услуга: {conv_data['service_name']}\n"
                f"📅 Дата: {day_name}, {conv_data['date'].strftime('%d.%m.%Y')}\n"
                f"⏰ Время: {time_str}\n\n"
                f"<i>Статус: подтверждено</i>"
            )
            print(f"[BOT] Создана запись #{appointment.id}: {conv_data['name']} на {conv_data['date']} {time_str}")

    finally:
        db.close()


async def main():
    """Основной цикл polling"""
    print(f"[BOT] Запуск polling для бота {BOT_NAME}...")
    print(f"[BOT] Token: {BOT_TOKEN[:20]}...")

    offset = None

    while True:
        try:
            updates = await get_updates(offset)

            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1

                    if "callback_query" in update:
                        await process_callback(update["callback_query"])

                    elif "message" in update:
                        message = update["message"]
                        text = message.get("text", "")
                        chat_id = message["chat"]["id"]
                        user_name = message.get("from", {}).get("first_name", "Unknown")

                        if text:
                            print(f"[BOT] Команда от {user_name} (chat_id={chat_id}): {text}")

                        if text == "/start" or text == "/help":
                            welcome = (
                                "Здравствуйте! 👩‍⚕️\n\n"
                                "<b>📋 Записи клиентов:</b>\n"
                                "/today - 📅 Записи на сегодня\n"
                                "/tomorrow - 📆 Записи на завтра\n"
                                "/week - 🗓 Записи на неделю\n"
                                "/slots - ⏰ Свободные слоты\n"
                                "/add - ✏️ Записать клиента вручную\n"
                                "/cancel - ❌ Отменить текущую операцию\n\n"
                                "<b>👩‍⚕️ Ваше расписание:</b>\n"
                                "/myschedule - Моё расписание\n"
                                "/schedule - Часы работы салона\n\n"
                                "<b>💅 Управление услугами:</b>\n"
                                "/services - Список услуг\n"
                                "/addservice - ➕ Добавить услугу\n"
                                "/delservice - ➖ Удалить услугу\n\n"
                                "<b>💬 Отзывы:</b>\n"
                                "/reviews - Отзывы на модерации\n\n"
                                "<i>Для повторного вызова меню: /help</i>"
                            )
                            await send_message(chat_id, welcome)

                        elif text == "/reviews":
                            db = SessionLocal()
                            try:
                                reviews = db.query(Review).filter(Review.is_published == False).order_by(Review.created_at.desc()).all()

                                if not reviews:
                                    await send_message(chat_id, "✅ Нет отзывов, ожидающих модерации.")
                                else:
                                    for review in reviews[:5]:
                                        stars = "⭐" * review.rating + "☆" * (5 - review.rating)
                                        created = review.created_at.strftime("%d.%m.%Y") if review.created_at else "—"

                                        text_msg = (
                                            f"💬 <b>ОТЗЫВ #{review.id}</b>\n"
                                            f"━━━━━━━━━━━━━━━━━━\n\n"
                                            f"{stars}  <b>({review.rating}/5)</b>\n\n"
                                            f"👤 <b>Клиент:</b> {review.name}\n"
                                            f"💆 <b>Услуга:</b> {review.service or '—'}\n\n"
                                            f"📝 <b>Текст:</b>\n"
                                            f"<i>\"{review.text}\"</i>\n\n"
                                            f"🕐 {created}"
                                        )

                                        keyboard = {
                                            "inline_keyboard": [[
                                                {"text": "✅ Опубликовать", "callback_data": f"review_approve_{review.id}"},
                                                {"text": "❌ Отклонить", "callback_data": f"review_reject_{review.id}"}
                                            ]]
                                        }

                                        await send_message_with_keyboard(chat_id, text_msg, keyboard)

                                    if len(reviews) > 5:
                                        await send_message(chat_id, f"<i>Показаны последние 5 из {len(reviews)} отзывов</i>")
                            finally:
                                db.close()

                        elif text == "/today":
                            db = SessionLocal()
                            try:
                                today = date.today()
                                appointments = db.query(Appointment).filter(
                                    Appointment.appointment_date == today,
                                    Appointment.status.in_(["pending", "confirmed"])
                                ).order_by(Appointment.appointment_time).all()

                                if not appointments:
                                    await send_message(chat_id, f"📅 <b>Сегодня ({today.strftime('%d.%m.%Y')})</b>\n\nЗаписей нет! 🎉")
                                else:
                                    text_msg = f"📅 <b>Записи на сегодня ({today.strftime('%d.%m.%Y')}):</b>\n\n"

                                    for apt in appointments:
                                        client = db.query(Client).filter(Client.id == apt.client_id).first()
                                        service = db.query(Service).filter(Service.id == apt.service_id).first()
                                        time_str = apt.appointment_time.strftime('%H:%M')
                                        status_emoji = "✅" if apt.status == "confirmed" else "⏳"

                                        text_msg += (
                                            f"{status_emoji} <b>{time_str}</b> — {service.name if service else 'Услуга'}\n"
                                            f"   👤 {client.name if client else 'Клиент'}\n"
                                            f"   📱 {client.phone if client else ''}\n\n"
                                        )

                                    text_msg += f"Всего записей: {len(appointments)}"
                                    await send_message(chat_id, text_msg)
                            finally:
                                db.close()

                        elif text == "/tomorrow":
                            db = SessionLocal()
                            try:
                                tomorrow = date.today() + timedelta(days=1)
                                day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                                day_name = day_names[tomorrow.weekday()]

                                appointments = db.query(Appointment).filter(
                                    Appointment.appointment_date == tomorrow,
                                    Appointment.status.in_(["pending", "confirmed"])
                                ).order_by(Appointment.appointment_time).all()

                                if not appointments:
                                    await send_message(chat_id, f"📆 <b>Завтра ({day_name}, {tomorrow.strftime('%d.%m.%Y')})</b>\n\nЗаписей нет! 🎉")
                                else:
                                    text_msg = f"📆 <b>Записи на завтра ({day_name}, {tomorrow.strftime('%d.%m.%Y')}):</b>\n\n"

                                    for apt in appointments:
                                        client = db.query(Client).filter(Client.id == apt.client_id).first()
                                        service = db.query(Service).filter(Service.id == apt.service_id).first()
                                        time_str = apt.appointment_time.strftime('%H:%M')
                                        status_emoji = "✅" if apt.status == "confirmed" else "⏳"

                                        text_msg += (
                                            f"{status_emoji} <b>{time_str}</b> — {service.name if service else 'Услуга'}\n"
                                            f"   👤 {client.name if client else 'Клиент'}\n"
                                            f"   📱 {client.phone if client else ''}\n\n"
                                        )

                                    text_msg += f"Всего записей: {len(appointments)}"
                                    await send_message(chat_id, text_msg)
                            finally:
                                db.close()

                        elif text == "/week":
                            db = SessionLocal()
                            try:
                                today = date.today()
                                week_end = today + timedelta(days=7)

                                appointments = db.query(Appointment).filter(
                                    Appointment.appointment_date >= today,
                                    Appointment.appointment_date < week_end,
                                    Appointment.status.in_(["pending", "confirmed"])
                                ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

                                if not appointments:
                                    await send_message(chat_id, f"🗓 <b>Записи на неделю</b>\n({today.strftime('%d.%m')} — {week_end.strftime('%d.%m.%Y')})\n\nЗаписей нет! 🎉")
                                else:
                                    text_msg = f"🗓 <b>Записи на неделю:</b>\n"
                                    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                                    current_date = None

                                    for apt in appointments:
                                        if apt.appointment_date != current_date:
                                            current_date = apt.appointment_date
                                            day_name = day_names[current_date.weekday()]
                                            text_msg += f"\n<b>{day_name}, {current_date.strftime('%d.%m')}:</b>\n"

                                        client = db.query(Client).filter(Client.id == apt.client_id).first()
                                        service = db.query(Service).filter(Service.id == apt.service_id).first()
                                        time_str = apt.appointment_time.strftime('%H:%M')
                                        status_emoji = "✅" if apt.status == "confirmed" else "⏳"

                                        text_msg += f"  {status_emoji} {time_str} — {client.name if client else '?'} ({service.name if service else '?'})\n"

                                    text_msg += f"\n📊 Всего: {len(appointments)} записей"
                                    await send_message(chat_id, text_msg)
                            finally:
                                db.close()

                        elif text == "/slots":
                            db = SessionLocal()
                            try:
                                check_date = date.today()
                                is_weekend = check_date.weekday() >= 5
                                work_start = dt_time(10, 0)
                                work_end = dt_time(18, 0) if is_weekend else dt_time(20, 0)
                                slot_duration = 30

                                appointments = db.query(Appointment).filter(
                                    Appointment.appointment_date == check_date,
                                    Appointment.status.in_(["pending", "confirmed"])
                                ).all()

                                booked_times = set()
                                for apt in appointments:
                                    apt_start = datetime.combine(check_date, apt.appointment_time)
                                    apt_end = apt_start + timedelta(minutes=apt.duration_minutes or 60)
                                    current = apt_start
                                    while current < apt_end:
                                        booked_times.add(current.time())
                                        current += timedelta(minutes=slot_duration)

                                all_slots = []
                                current_time = work_start
                                while current_time < work_end:
                                    all_slots.append(current_time)
                                    current_dt = datetime.combine(check_date, current_time)
                                    current_dt += timedelta(minutes=slot_duration)
                                    current_time = current_dt.time()

                                free_slots = [t for t in all_slots if t not in booked_times]
                                busy_slots = [t for t in all_slots if t in booked_times]

                                day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                                day_name = day_names[check_date.weekday()]

                                text_msg = f"📅 <b>{day_name}, {check_date.strftime('%d.%m.%Y')}</b>\n"
                                text_msg += f"⏰ Рабочие часы: {work_start.strftime('%H:%M')} — {work_end.strftime('%H:%M')}\n\n"

                                if free_slots:
                                    text_msg += f"✅ <b>Свободные слоты ({len(free_slots)}):</b>\n"
                                    morning = [t for t in free_slots if t.hour < 12]
                                    afternoon = [t for t in free_slots if 12 <= t.hour < 17]
                                    evening = [t for t in free_slots if t.hour >= 17]

                                    if morning:
                                        text_msg += f"🌅 Утро: {', '.join(t.strftime('%H:%M') for t in morning)}\n"
                                    if afternoon:
                                        text_msg += f"☀️ День: {', '.join(t.strftime('%H:%M') for t in afternoon)}\n"
                                    if evening:
                                        text_msg += f"🌙 Вечер: {', '.join(t.strftime('%H:%M') for t in evening)}\n"
                                else:
                                    text_msg += "❌ Все слоты заняты!\n"

                                text_msg += f"\n📊 Занято: {len(busy_slots)} / {len(all_slots)} слотов"
                                await send_message(chat_id, text_msg)
                            finally:
                                db.close()

                        elif text == "/services":
                            db = SessionLocal()
                            try:
                                services = db.query(Service).filter(Service.is_active == True).all()

                                if not services:
                                    await send_message(chat_id, "К сожалению, услуги пока не добавлены.")
                                else:
                                    text_msg = "💅 <b>Наши услуги:</b>\n\n"

                                    categories = {}
                                    for service in services:
                                        cat = service.category or "Другое"
                                        if cat not in categories:
                                            categories[cat] = []
                                        categories[cat].append(service)

                                    for category, cat_services in categories.items():
                                        text_msg += f"<b>{category}</b>\n"
                                        for service in cat_services:
                                            text_msg += f"• {service.name}\n  {service.duration_minutes} мин | {service.price} ₽\n"
                                        text_msg += "\n"

                                    await send_message(chat_id, text_msg)
                            finally:
                                db.close()

                        elif text == "/myschedule":
                            await send_message(chat_id,
                                "👩‍⚕️ <b>Моё расписание</b>\n\n"
                                "🕐 Пн-Пт: 10:00 — 20:00\n"
                                "🕐 Сб-Вс: 10:00 — 18:00\n\n"
                                "<i>Для изменения расписания используйте полную версию бота.</i>"
                            )

                        elif text == "/schedule":
                            await send_message(chat_id,
                                "📅 <b>Часы работы салона</b>\n\n"
                                "🕐 Пн-Пт: 10:00 — 20:00\n"
                                "🕐 Сб-Вс: 10:00 — 18:00\n\n"
                                "<i>Для изменения используйте полную версию бота.</i>"
                            )

                        elif text == "/block":
                            await send_message(chat_id, "🚫 Команда /block требует интерактивного режима.\n\n<i>Используйте полную версию бота для блокировки слотов.</i>")

                        elif text == "/unblock":
                            await send_message(chat_id, "✅ Команда /unblock требует интерактивного режима.\n\n<i>Используйте полную версию бота для разблокировки слотов.</i>")

                        elif text == "/add" or text == "/cancel":
                            if text == "/cancel" and chat_id in conversations:
                                del conversations[chat_id]
                                await send_message(chat_id, "❌ Запись отменена.")
                            else:
                                # Начинаем интерактивную запись
                                conversations[chat_id] = {"step": "name", "data": {}}
                                await send_message(chat_id,
                                    "✏️ <b>Ручная запись клиента</b>\n\n"
                                    "Шаг 1/5: Введите <b>имя клиента</b>\n\n"
                                    "<i>Для отмены: /cancel</i>"
                                )

                        elif text == "/edit":
                            await send_message(chat_id, "✏️ Команда /edit требует интерактивного режима.\n\n<i>Используйте полную версию бота для редактирования услуг.</i>")

                        elif text == "/reminders":
                            await send_message(chat_id, "📬 Команда /reminders требует интерактивного режима.\n\n<i>Напоминания будут отправлены автоматически за день до записи.</i>")

                        elif text.startswith("/addservice"):
                            # Формат: /addservice Название | Категория | Цена | Длительность | Описание
                            parts = text.replace("/addservice", "").strip()
                            if not parts:
                                await send_message(chat_id,
                                    "➕ <b>Добавление услуги</b>\n\n"
                                    "Формат:\n"
                                    "<code>/addservice Название | Категория | Цена | Минуты | Описание</code>\n\n"
                                    "Пример:\n"
                                    "<code>/addservice Чистка лица | Уход за лицом | 3000 | 60 | Глубокое очищение</code>"
                                )
                            else:
                                try:
                                    data = [p.strip() for p in parts.split("|")]
                                    if len(data) < 4:
                                        await send_message(chat_id, "❌ Недостаточно данных. Нужно минимум: Название | Категория | Цена | Минуты")
                                    else:
                                        name = data[0]
                                        category = data[1]
                                        price = int(data[2])
                                        duration = int(data[3])
                                        description = data[4] if len(data) > 4 else ""

                                        db = SessionLocal()
                                        try:
                                            new_service = Service(
                                                name=name,
                                                category=category,
                                                price=price,
                                                duration_minutes=duration,
                                                description=description,
                                                is_active=True
                                            )
                                            db.add(new_service)
                                            db.commit()
                                            db.refresh(new_service)

                                            await send_message(chat_id,
                                                f"✅ <b>Услуга добавлена!</b>\n\n"
                                                f"🆔 ID: {new_service.id}\n"
                                                f"📝 {name}\n"
                                                f"📂 {category}\n"
                                                f"💰 {price} ₽\n"
                                                f"⏱ {duration} мин"
                                            )
                                            print(f"[BOT] Добавлена услуга: {name}")
                                        finally:
                                            db.close()
                                except ValueError:
                                    await send_message(chat_id, "❌ Ошибка: цена и длительность должны быть числами.")
                                except Exception as e:
                                    await send_message(chat_id, f"❌ Ошибка: {e}")

                        elif text.startswith("/delservice"):
                            # Формат: /delservice ID
                            parts = text.replace("/delservice", "").strip()
                            if not parts:
                                db = SessionLocal()
                                try:
                                    services = db.query(Service).filter(Service.is_active == True).all()
                                    if not services:
                                        await send_message(chat_id, "Услуг нет.")
                                    else:
                                        text_msg = "➖ <b>Удаление услуги</b>\n\nВведите:\n<code>/delservice ID</code>\n\n<b>Активные услуги:</b>\n"
                                        for s in services:
                                            text_msg += f"🆔 <b>{s.id}</b> — {s.name} ({s.price} ₽)\n"
                                        await send_message(chat_id, text_msg)
                                finally:
                                    db.close()
                            else:
                                try:
                                    service_id = int(parts)
                                    db = SessionLocal()
                                    try:
                                        service = db.query(Service).filter(Service.id == service_id).first()
                                        if service:
                                            service_name = service.name
                                            service.is_active = False  # Деактивируем вместо удаления
                                            db.commit()
                                            await send_message(chat_id, f"✅ Услуга «{service_name}» деактивирована.")
                                            print(f"[BOT] Деактивирована услуга: {service_name}")
                                        else:
                                            await send_message(chat_id, f"❌ Услуга с ID {service_id} не найдена.")
                                    finally:
                                        db.close()
                                except ValueError:
                                    await send_message(chat_id, "❌ ID должен быть числом.")

                        # Обработка шагов интерактивной записи
                        elif chat_id in conversations and text and not text.startswith("/"):
                            conv = conversations[chat_id]
                            step = conv["step"]

                            if step == "name":
                                conv["data"]["name"] = text.strip()
                                conv["step"] = "phone"
                                await send_message(chat_id,
                                    f"✅ Имя: <b>{text.strip()}</b>\n\n"
                                    "Шаг 2/5: Введите <b>телефон клиента</b>\n"
                                    "<i>Например: +79001234567</i>"
                                )

                            elif step == "phone":
                                phone = normalize_phone(text.strip())
                                if not phone:
                                    await send_message(chat_id,
                                        "❌ <b>Некорректный номер телефона</b>\n\n"
                                        "Введите номер в формате:\n"
                                        "• +79001234567\n"
                                        "• 89001234567\n"
                                        "• 9001234567"
                                    )
                                else:
                                    conv["data"]["phone"] = phone
                                    conv["step"] = "service"

                                    # Показываем услуги кнопками
                                    db = SessionLocal()
                                    try:
                                        services = db.query(Service).filter(Service.is_active == True).all()
                                        if not services:
                                            await send_message(chat_id, "❌ Услуги не найдены. Сначала добавьте услуги через /addservice")
                                            del conversations[chat_id]
                                        else:
                                            buttons = []
                                            for s in services:
                                                buttons.append([{"text": f"{s.name} ({s.price}₽)", "callback_data": f"add_service_{s.id}"}])

                                            keyboard = {"inline_keyboard": buttons}
                                            await send_message_with_keyboard(chat_id,
                                                f"✅ Телефон: <b>{phone}</b>\n\n"
                                                "Шаг 3/5: Выберите <b>услугу</b>:",
                                                keyboard
                                            )
                                    finally:
                                        db.close()

        except Exception as e:
            print(f"[BOT] Ошибка: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
