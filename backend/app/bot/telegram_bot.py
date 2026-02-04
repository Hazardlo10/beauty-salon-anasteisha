"""
Telegram бот для онлайн-записи
Клиенты могут записываться на прием прямо через Telegram!
"""
import os
import sys
from datetime import datetime, timedelta, date, time as dt_time
from typing import Optional

# Добавляем путь к родительской директории для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import SessionLocal
from app.models.client import Client
from app.models.service import Service
from app.models.appointment import Appointment
from app.models.notification import Notification
from app.config import get_settings

settings = get_settings()

# Состояния разговора для клиентов
SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, ENTERING_PHONE, ENTERING_NAME, CONFIRMING = range(6)

# Состояния для ручной записи специалистом
MANUAL_SERVICE, MANUAL_DATE, MANUAL_TIME, MANUAL_CLIENT_NAME, MANUAL_CLIENT_PHONE, MANUAL_CONFIRM = range(100, 106)


def get_db() -> Session:
    """Получить сессию базы данных"""
    return SessionLocal()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    user = update.effective_user
    telegram_id = user.id

    # Проверяем, является ли пользователь специалистом
    specialist = is_specialist(telegram_id)

    # Проверяем, есть ли клиент в базе
    db = get_db()
    try:
        client = db.query(Client).filter(Client.telegram_id == telegram_id).first()

        if specialist:
            welcome_text = "Здравствуйте! 👩‍⚕️\n\n"
            welcome_text += (
                "*Команды для специалиста:*\n"
                "/today - 📅 Записи на сегодня\n"
                "/tomorrow - 📆 Записи на завтра\n"
                "/week - 🗓 Записи на неделю\n"
                "/slots - ⏰ Свободные слоты\n"
                "/add - ✏️ Записать клиента вручную\n\n"
                "*Общие команды:*\n"
                "/services - 💅 Список услуг\n"
            )
        elif client:
            welcome_text = f"С возвращением, {client.name}! 🌸\n\n"
            welcome_text += (
                "Я бот для онлайн-записи в косметологический кабинет.\n\n"
                "Доступные команды:\n"
                "/book - 📅 Записаться на прием\n"
                "/myappointments - 📋 Мои записи\n"
                "/services - 💅 Список услуг\n"
                "/cancel - ❌ Отменить запись\n"
            )
        else:
            welcome_text = "Здравствуйте! 🌸\n\n"
            welcome_text += (
                "Я бот для онлайн-записи в косметологический кабинет.\n\n"
                "Доступные команды:\n"
                "/book - 📅 Записаться на прием\n"
                "/myappointments - 📋 Мои записи\n"
                "/services - 💅 Список услуг\n"
                "/cancel - ❌ Отменить запись\n"
            )

        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    finally:
        db.close()


async def services_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /services - список всех услуг"""
    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()

        if not services:
            await update.message.reply_text("К сожалению, услуги пока не добавлены.")
            return

        text = "💅 *Наши услуги:*\n\n"

        # Группируем по категориям
        categories = {}
        for service in services:
            cat = service.category or "Другое"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(service)

        for category, cat_services in categories.items():
            text += f"*{category}*\n"
            for service in cat_services:
                text += (
                    f"• {service.name}\n"
                    f"  {service.duration_minutes} мин | {service.price} ₽\n"
                )
                if service.description:
                    text += f"  _{service.description}_\n"
            text += "\n"

        text += "Для записи используйте /book"

        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса записи - выбор услуги"""
    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()

        if not services:
            await update.message.reply_text("К сожалению, услуги пока не добавлены.")
            return ConversationHandler.END

        # Создаем инлайн-клавиатуру с услугами
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price}₽",
                    callback_data=f"service_{service.id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Выберите услугу:",
            reply_markup=reply_markup
        )

        return SELECTING_SERVICE
    finally:
        db.close()


async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора услуги"""
    query = update.callback_query
    await query.answer()

    service_id = int(query.data.split("_")[1])
    context.user_data["service_id"] = service_id

    db = get_db()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        context.user_data["service_name"] = service.name
        context.user_data["service_price"] = float(service.price)
        context.user_data["service_duration"] = service.duration_minutes
    finally:
        db.close()

    # Предлагаем выбрать дату
    keyboard = []
    today = date.today()

    for i in range(7):  # Ближайшие 7 дней
        day = today + timedelta(days=i)
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][day.weekday()]
        keyboard.append([
            InlineKeyboardButton(
                f"{day_name}, {day.strftime('%d.%m.%Y')}",
                callback_data=f"date_{day.isoformat()}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Вы выбрали: {service.name}\n"
        f"Стоимость: {service.price}₽\n\n"
        "Выберите дату:",
        reply_markup=reply_markup
    )

    return SELECTING_DATE


async def date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора даты"""
    query = update.callback_query
    await query.answer()

    selected_date = query.data.split("_")[1]
    context.user_data["date"] = selected_date

    # Получаем доступные слоты времени
    db = get_db()
    try:
        # Рабочие часы (например, 9:00 - 18:00)
        work_start = dt_time(9, 0)
        work_end = dt_time(18, 0)
        slot_duration = 30  # минут

        # Получаем занятые слоты на эту дату
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == selected_date,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).all()

        booked_times = [apt.appointment_time for apt in appointments]

        # Генерируем доступные слоты
        available_slots = []
        current_time = work_start

        while current_time < work_end:
            if current_time not in booked_times:
                available_slots.append(current_time)

            # Увеличиваем время на slot_duration
            current_datetime = datetime.combine(date.today(), current_time)
            current_datetime += timedelta(minutes=slot_duration)
            current_time = current_datetime.time()

        if not available_slots:
            await query.edit_message_text(
                "К сожалению, на эту дату все слоты заняты.\n"
                "Попробуйте выбрать другую дату.",
            )
            return SELECTING_DATE

        # Создаем клавиатуру со временем
        keyboard = []
        for slot_time in available_slots[:12]:  # Показываем первые 12 слотов
            keyboard.append([
                InlineKeyboardButton(
                    slot_time.strftime("%H:%M"),
                    callback_data=f"time_{slot_time.strftime('%H:%M')}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Дата: {datetime.fromisoformat(selected_date).strftime('%d.%m.%Y')}\n\n"
            "Выберите время:",
            reply_markup=reply_markup
        )

        return SELECTING_TIME
    finally:
        db.close()


async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени"""
    query = update.callback_query
    await query.answer()

    selected_time = query.data.split("_")[1]
    context.user_data["time"] = selected_time

    # Проверяем, есть ли пользователь в базе
    telegram_id = update.effective_user.id
    db = get_db()
    try:
        client = db.query(Client).filter(Client.telegram_id == telegram_id).first()

        if client:
            # Клиент уже есть - показываем подтверждение
            context.user_data["client_id"] = client.id
            context.user_data["client_name"] = client.name
            context.user_data["client_phone"] = client.phone

            await show_confirmation(query, context)
            return CONFIRMING
        else:
            # Новый клиент - запрашиваем имя
            await query.edit_message_text(
                "Как вас зовут? (Введите ваше имя)"
            )
            return ENTERING_NAME
    finally:
        db.close()


async def name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    name = update.message.text.strip()
    context.user_data["client_name"] = name

    await update.message.reply_text(
        f"Приятно познакомиться, {name}!\n\n"
        "Введите ваш номер телефона в формате +79XXXXXXXXX:"
    )

    return ENTERING_PHONE


async def phone_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода телефона"""
    phone = update.message.text.strip()

    # Простая валидация телефона
    if not phone.startswith("+7") or len(phone) != 12:
        await update.message.reply_text(
            "Неверный формат телефона.\n"
            "Пожалуйста, введите в формате +79XXXXXXXXX:"
        )
        return ENTERING_PHONE

    context.user_data["client_phone"] = phone

    # Показываем подтверждение
    await show_confirmation_message(update, context)

    return CONFIRMING


async def show_confirmation(query, context):
    """Показать подтверждение записи (через callback query)"""
    service_name = context.user_data["service_name"]
    service_price = context.user_data["service_price"]
    date_str = datetime.fromisoformat(context.user_data["date"]).strftime('%d.%m.%Y')
    time_str = context.user_data["time"]
    client_name = context.user_data["client_name"]
    client_phone = context.user_data["client_phone"]

    text = (
        "📋 *Подтверждение записи:*\n\n"
        f"👤 Клиент: {client_name}\n"
        f"📱 Телефон: {client_phone}\n\n"
        f"💅 Услуга: {service_name}\n"
        f"💰 Стоимость: {service_price} ₽\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n\n"
        "Подтверждаете запись?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, подтверждаю", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def show_confirmation_message(update, context):
    """Показать подтверждение записи (через сообщение)"""
    service_name = context.user_data["service_name"]
    service_price = context.user_data["service_price"]
    date_str = datetime.fromisoformat(context.user_data["date"]).strftime('%d.%m.%Y')
    time_str = context.user_data["time"]
    client_name = context.user_data["client_name"]
    client_phone = context.user_data["client_phone"]

    text = (
        "📋 *Подтверждение записи:*\n\n"
        f"👤 Клиент: {client_name}\n"
        f"📱 Телефон: {client_phone}\n\n"
        f"💅 Услуга: {service_name}\n"
        f"💰 Стоимость: {service_price} ₽\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n\n"
        "Подтверждаете запись?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, подтверждаю", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение записи - сохранение в БД"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("Запись отменена. Используйте /book для новой записи.")
        return ConversationHandler.END

    # Сохраняем запись в базу данных
    db = get_db()
    try:
        # Проверяем, не занят ли слот (защита от дублей!)
        existing_slot = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == context.user_data["date"],
                Appointment.appointment_time == context.user_data["time"],
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).first()

        if existing_slot:
            await query.edit_message_text(
                "❌ К сожалению, это время только что заняли.\n\n"
                "Пожалуйста, используйте /book чтобы выбрать другое время."
            )
            return ConversationHandler.END

        telegram_id = update.effective_user.id
        telegram_username = update.effective_user.username

        # Создаем или получаем клиента
        client = db.query(Client).filter(Client.telegram_id == telegram_id).first()

        if not client:
            # Создаем нового клиента
            client = Client(
                name=context.user_data["client_name"],
                phone=context.user_data["client_phone"],
                telegram_id=telegram_id,
                telegram_username=telegram_username
            )
            db.add(client)
            db.commit()
            db.refresh(client)

        # Создаем запись на прием
        appointment = Appointment(
            client_id=client.id,
            service_id=context.user_data["service_id"],
            appointment_date=context.user_data["date"],
            appointment_time=context.user_data["time"],
            status="pending",
            duration_minutes=context.user_data["service_duration"],
            total_price=context.user_data["service_price"],
            payment_status="unpaid"
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        # Создаем уведомление
        notification = Notification(
            appointment_id=appointment.id,
            notification_type="telegram",
            message=f"Запись создана: {context.user_data['date']} {context.user_data['time']}",
            status="sent"
        )
        db.add(notification)
        db.commit()

        # Отправляем подтверждение
        date_str = datetime.fromisoformat(context.user_data["date"]).strftime('%d.%m.%Y')

        await query.edit_message_text(
            f"✅ *Запись подтверждена!*\n\n"
            f"📅 {date_str} в {context.user_data['time']}\n"
            f"💅 {context.user_data['service_name']}\n"
            f"💰 {context.user_data['service_price']} ₽\n\n"
            f"Мы отправим вам напоминание за день до визита.\n\n"
            f"Для просмотра ваших записей используйте /myappointments",
            parse_mode="Markdown"
        )

        # Уведомляем админа (если настроено)
        if settings.TELEGRAM_ADMIN_CHAT_ID:
            admin_text = (
                "🔔 *Новая запись!*\n\n"
                f"👤 Клиент: {context.user_data['client_name']}\n"
                f"📱 Телефон: {context.user_data['client_phone']}\n"
                f"📅 Дата: {date_str} в {context.user_data['time']}\n"
                f"💅 Услуга: {context.user_data['service_name']}\n"
                f"💰 Стоимость: {context.user_data['service_price']} ₽"
            )
            try:
                await context.bot.send_message(
                    chat_id=settings.TELEGRAM_ADMIN_CHAT_ID,
                    text=admin_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление админу: {e}")

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при создании записи: {str(e)}\n\n"
            "Попробуйте позже или свяжитесь с нами по телефону."
        )
        return ConversationHandler.END
    finally:
        db.close()


async def my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myappointments - показать записи клиента"""
    telegram_id = update.effective_user.id

    db = get_db()
    try:
        client = db.query(Client).filter(Client.telegram_id == telegram_id).first()

        if not client:
            await update.message.reply_text(
                "У вас пока нет записей.\n"
                "Используйте /book для записи на прием."
            )
            return

        # Получаем активные записи
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.client_id == client.id,
                Appointment.status.in_(["pending", "confirmed"]),
                Appointment.appointment_date >= date.today()
            )
        ).all()

        if not appointments:
            await update.message.reply_text("У вас нет активных записей.")
            return

        text = "📋 *Ваши записи:*\n\n"

        for apt in appointments:
            service = db.query(Service).filter(Service.id == apt.service_id).first()
            date_str = apt.appointment_date.strftime('%d.%m.%Y')
            time_str = apt.appointment_time.strftime('%H:%M')

            text += (
                f"📅 {date_str} в {time_str}\n"
                f"💅 {service.name}\n"
                f"💰 {apt.total_price} ₽\n"
                f"📊 Статус: {apt.status}\n\n"
            )

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        db.close()


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


# ==================== КОМАНДЫ ДЛЯ СПЕЦИАЛИСТА ====================

def is_specialist(user_id: int) -> bool:
    """Проверить, является ли пользователь специалистом"""
    salon_chat_id = settings.TELEGRAM_SALON_CHAT_ID
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    allowed_ids = []
    if salon_chat_id:
        allowed_ids.append(int(salon_chat_id))
    if admin_chat_id:
        allowed_ids.append(int(admin_chat_id))
    return user_id in allowed_ids


async def today_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /today - записи на сегодня (только для специалиста)"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return

    db = get_db()
    try:
        today = date.today()
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == today,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).order_by(Appointment.appointment_time).all()

        if not appointments:
            await update.message.reply_text(
                f"📅 *Сегодня ({today.strftime('%d.%m.%Y')})*\n\n"
                "Записей нет! 🎉",
                parse_mode="Markdown"
            )
            return

        text = f"📅 *Записи на сегодня ({today.strftime('%d.%m.%Y')}):*\n\n"

        for apt in appointments:
            client = db.query(Client).filter(Client.id == apt.client_id).first()
            service = db.query(Service).filter(Service.id == apt.service_id).first()
            time_str = apt.appointment_time.strftime('%H:%M')
            status_emoji = "✅" if apt.status == "confirmed" else "⏳"

            text += (
                f"{status_emoji} *{time_str}* — {service.name if service else 'Услуга'}\n"
                f"   👤 {client.name if client else 'Клиент'}\n"
                f"   📱 {client.phone if client else ''}\n\n"
            )

        text += f"Всего записей: {len(appointments)}"

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        db.close()


async def tomorrow_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /tomorrow - записи на завтра (только для специалиста)"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return

    db = get_db()
    try:
        tomorrow = date.today() + timedelta(days=1)
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[tomorrow.weekday()]

        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == tomorrow,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).order_by(Appointment.appointment_time).all()

        if not appointments:
            await update.message.reply_text(
                f"📅 *Завтра ({day_name}, {tomorrow.strftime('%d.%m.%Y')})*\n\n"
                "Записей нет! 🎉",
                parse_mode="Markdown"
            )
            return

        text = f"📅 *Записи на завтра ({day_name}, {tomorrow.strftime('%d.%m.%Y')}):*\n\n"

        for apt in appointments:
            client = db.query(Client).filter(Client.id == apt.client_id).first()
            service = db.query(Service).filter(Service.id == apt.service_id).first()
            time_str = apt.appointment_time.strftime('%H:%M')
            status_emoji = "✅" if apt.status == "confirmed" else "⏳"

            text += (
                f"{status_emoji} *{time_str}* — {service.name if service else 'Услуга'}\n"
                f"   👤 {client.name if client else 'Клиент'}\n"
                f"   📱 {client.phone if client else ''}\n\n"
            )

        text += f"Всего записей: {len(appointments)}"

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        db.close()


async def week_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /week - записи на неделю (только для специалиста)"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return

    db = get_db()
    try:
        today = date.today()
        week_end = today + timedelta(days=7)

        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date >= today,
                Appointment.appointment_date < week_end,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

        if not appointments:
            await update.message.reply_text(
                f"📅 *Записи на неделю*\n"
                f"({today.strftime('%d.%m')} — {week_end.strftime('%d.%m.%Y')})\n\n"
                "Записей нет! 🎉",
                parse_mode="Markdown"
            )
            return

        text = f"📅 *Записи на неделю:*\n\n"
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        current_date = None

        for apt in appointments:
            # Новый день
            if apt.appointment_date != current_date:
                current_date = apt.appointment_date
                day_name = day_names[current_date.weekday()]
                text += f"\n*{day_name}, {current_date.strftime('%d.%m')}:*\n"

            client = db.query(Client).filter(Client.id == apt.client_id).first()
            service = db.query(Service).filter(Service.id == apt.service_id).first()
            time_str = apt.appointment_time.strftime('%H:%M')
            status_emoji = "✅" if apt.status == "confirmed" else "⏳"

            text += f"  {status_emoji} {time_str} — {client.name if client else '?'} ({service.name if service else '?'})\n"

        text += f"\n📊 Всего: {len(appointments)} записей"

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        db.close()


async def available_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /slots - свободные слоты (только для специалиста)"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return

    # Парсим дату из аргументов (по умолчанию - сегодня)
    args = context.args
    if args:
        try:
            check_date = datetime.strptime(args[0], "%d.%m.%Y").date()
        except ValueError:
            try:
                check_date = datetime.strptime(args[0], "%d.%m").date()
                check_date = check_date.replace(year=date.today().year)
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат даты.\n"
                    "Используйте: /slots или /slots 15.02.2025"
                )
                return
    else:
        check_date = date.today()

    db = get_db()
    try:
        # Определяем рабочие часы
        is_weekend = check_date.weekday() >= 5
        if is_weekend:
            work_start = dt_time(10, 0)
            work_end = dt_time(18, 0)
        else:
            work_start = dt_time(10, 0)
            work_end = dt_time(20, 0)

        slot_duration = 30  # минут

        # Получаем занятые слоты
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == check_date,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).all()

        booked_times = set()
        for apt in appointments:
            # Учитываем длительность процедуры
            apt_start = datetime.combine(check_date, apt.appointment_time)
            apt_end = apt_start + timedelta(minutes=apt.duration_minutes)
            current = apt_start
            while current < apt_end:
                booked_times.add(current.time())
                current += timedelta(minutes=slot_duration)

        # Генерируем все слоты
        all_slots = []
        current_time = work_start
        while current_time < work_end:
            all_slots.append(current_time)
            current_dt = datetime.combine(check_date, current_time)
            current_dt += timedelta(minutes=slot_duration)
            current_time = current_dt.time()

        # Разделяем на свободные и занятые
        free_slots = [t for t in all_slots if t not in booked_times]
        busy_slots = [t for t in all_slots if t in booked_times]

        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[check_date.weekday()]

        text = f"📅 *{day_name}, {check_date.strftime('%d.%m.%Y')}*\n"
        text += f"⏰ Рабочие часы: {work_start.strftime('%H:%M')} — {work_end.strftime('%H:%M')}\n\n"

        if free_slots:
            text += f"✅ *Свободные слоты ({len(free_slots)}):*\n"
            # Группируем по периодам
            morning = [t for t in free_slots if t.hour < 12]
            afternoon = [t for t in free_slots if 12 <= t.hour < 17]
            evening = [t for t in free_slots if t.hour >= 17]

            if morning:
                text += f"🌅 Утро: {', '.join(t.strftime('%H:%M') for t in morning)}\n"
            if afternoon:
                text += f"☀️ День: {', '.join(t.strftime('%H:%M') for t in afternoon)}\n"
            if evening:
                text += f"🌙 Вечер: {', '.join(t.strftime('%H:%M') for t in evening)}\n"
        else:
            text += "❌ Все слоты заняты!\n"

        text += f"\n📊 Занято: {len(busy_slots)} / {len(all_slots)} слотов"

        await update.message.reply_text(text, parse_mode="Markdown")

    finally:
        db.close()


# ==================== РУЧНАЯ ЗАПИСЬ КЛИЕНТА ====================

async def manual_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add - начать ручную запись клиента"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return ConversationHandler.END

    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()

        if not services:
            await update.message.reply_text("Услуги не добавлены в базу.")
            return ConversationHandler.END

        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} — {service.price}₽",
                    callback_data=f"madd_svc_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="madd_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📝 *Ручная запись клиента*\n\n"
            "Шаг 1/5: Выберите услугу:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return MANUAL_SERVICE
    finally:
        db.close()


async def manual_service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор услуги для ручной записи"""
    query = update.callback_query
    await query.answer()

    if query.data == "madd_cancel":
        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    service_id = int(query.data.split("_")[2])
    context.user_data["manual_service_id"] = service_id

    db = get_db()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        context.user_data["manual_service_name"] = service.name
        context.user_data["manual_service_price"] = float(service.price)
        context.user_data["manual_service_duration"] = service.duration_minutes
    finally:
        db.close()

    # Выбор даты
    keyboard = []
    today = date.today()
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    for i in range(14):  # 2 недели
        day = today + timedelta(days=i)
        day_name = day_names[day.weekday()]
        keyboard.append([
            InlineKeyboardButton(
                f"{day_name}, {day.strftime('%d.%m')}",
                callback_data=f"madd_date_{day.isoformat()}"
            )
        ])

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="madd_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ Услуга: {service.name}\n\n"
        "Шаг 2/5: Выберите дату:",
        reply_markup=reply_markup
    )

    return MANUAL_DATE


async def manual_date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты для ручной записи"""
    query = update.callback_query
    await query.answer()

    if query.data == "madd_cancel":
        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    selected_date = query.data.split("_")[2]
    context.user_data["manual_date"] = selected_date

    # Получаем свободные слоты
    db = get_db()
    try:
        check_date = datetime.fromisoformat(selected_date).date()
        is_weekend = check_date.weekday() >= 5

        if is_weekend:
            work_start = dt_time(10, 0)
            work_end = dt_time(18, 0)
        else:
            work_start = dt_time(10, 0)
            work_end = dt_time(20, 0)

        slot_duration = 30

        # Занятые слоты
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == selected_date,
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).all()

        booked_times = set()
        for apt in appointments:
            apt_start = datetime.combine(check_date, apt.appointment_time)
            apt_end = apt_start + timedelta(minutes=apt.duration_minutes)
            current = apt_start
            while current < apt_end:
                booked_times.add(current.time())
                current += timedelta(minutes=slot_duration)

        # Свободные слоты
        free_slots = []
        current_time = work_start
        while current_time < work_end:
            if current_time not in booked_times:
                free_slots.append(current_time)
            current_dt = datetime.combine(check_date, current_time)
            current_dt += timedelta(minutes=slot_duration)
            current_time = current_dt.time()

        if not free_slots:
            await query.edit_message_text(
                "❌ На эту дату нет свободных слотов.\n"
                "Используйте /add для выбора другой даты."
            )
            return ConversationHandler.END

        # Группируем слоты по 4 в ряд
        keyboard = []
        row = []
        for slot in free_slots:
            row.append(InlineKeyboardButton(
                slot.strftime("%H:%M"),
                callback_data=f"madd_time_{slot.strftime('%H:%M')}"
            ))
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="madd_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[check_date.weekday()]

        await query.edit_message_text(
            f"✅ Услуга: {context.user_data['manual_service_name']}\n"
            f"✅ Дата: {day_name}, {check_date.strftime('%d.%m.%Y')}\n\n"
            f"Шаг 3/5: Выберите время ({len(free_slots)} слотов):",
            reply_markup=reply_markup
        )

        return MANUAL_TIME

    finally:
        db.close()


async def manual_time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени для ручной записи"""
    query = update.callback_query
    await query.answer()

    if query.data == "madd_cancel":
        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    selected_time = query.data.split("_")[2]
    context.user_data["manual_time"] = selected_time

    await query.edit_message_text(
        f"✅ Услуга: {context.user_data['manual_service_name']}\n"
        f"✅ Дата: {context.user_data['manual_date']}\n"
        f"✅ Время: {selected_time}\n\n"
        "Шаг 4/5: Введите *имя клиента*:",
        parse_mode="Markdown"
    )

    return MANUAL_CLIENT_NAME


async def manual_client_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод имени клиента"""
    name = update.message.text.strip()
    context.user_data["manual_client_name"] = name

    await update.message.reply_text(
        f"✅ Имя: {name}\n\n"
        "Шаг 5/5: Введите *номер телефона* клиента (или - если неизвестен):",
        parse_mode="Markdown"
    )

    return MANUAL_CLIENT_PHONE


async def manual_client_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод телефона клиента и подтверждение"""
    phone = update.message.text.strip()
    if phone == "-":
        phone = None
    context.user_data["manual_client_phone"] = phone

    # Показываем подтверждение
    date_obj = datetime.fromisoformat(context.user_data["manual_date"]).date()
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    text = (
        "📋 *Подтверждение записи:*\n\n"
        f"👤 Клиент: {context.user_data['manual_client_name']}\n"
        f"📱 Телефон: {phone or 'не указан'}\n\n"
        f"💅 Услуга: {context.user_data['manual_service_name']}\n"
        f"💰 Стоимость: {context.user_data['manual_service_price']} ₽\n"
        f"📅 Дата: {day_names[date_obj.weekday()]}, {date_obj.strftime('%d.%m.%Y')}\n"
        f"🕐 Время: {context.user_data['manual_time']}\n\n"
        "Сохранить запись?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Сохранить", callback_data="madd_save")],
        [InlineKeyboardButton("❌ Отмена", callback_data="madd_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    return MANUAL_CONFIRM


async def manual_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение ручной записи"""
    query = update.callback_query
    await query.answer()

    if query.data == "madd_cancel":
        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    db = get_db()
    try:
        # Проверяем, не занят ли слот (защита от дублей!)
        existing_slot = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == context.user_data["manual_date"],
                Appointment.appointment_time == context.user_data["manual_time"],
                Appointment.status.in_(["pending", "confirmed"])
            )
        ).first()

        if existing_slot:
            await query.edit_message_text(
                "❌ *Ошибка: это время уже занято!*\n\n"
                "Возможно, кто-то записался через сайт.\n"
                "Используйте /slots чтобы увидеть свободные слоты.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

        # Ищем или создаём клиента
        phone = context.user_data.get("manual_client_phone")
        name = context.user_data["manual_client_name"]

        client = None
        if phone:
            client = db.query(Client).filter(Client.phone == phone).first()

        if not client:
            client = Client(
                name=name,
                phone=phone or f"manual_{datetime.now().timestamp()}"
            )
            db.add(client)
            db.commit()
            db.refresh(client)

        # Создаём запись
        appointment = Appointment(
            client_id=client.id,
            service_id=context.user_data["manual_service_id"],
            appointment_date=context.user_data["manual_date"],
            appointment_time=context.user_data["manual_time"],
            status="confirmed",  # Сразу подтверждённая
            duration_minutes=context.user_data["manual_service_duration"],
            total_price=context.user_data["manual_service_price"],
            payment_status="unpaid",
            notes="Ручная запись через Telegram"
        )
        db.add(appointment)
        db.commit()

        await query.edit_message_text(
            f"✅ *Запись сохранена!*\n\n"
            f"👤 {name}\n"
            f"📅 {context.user_data['manual_date']} в {context.user_data['manual_time']}\n"
            f"💅 {context.user_data['manual_service_name']}",
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def manual_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена ручной записи"""
    await update.message.reply_text("Запись отменена.")
    return ConversationHandler.END


async def send_specialist_welcome(application):
    """Отправить инструкцию специалисту при запуске бота"""
    salon_chat_id = settings.TELEGRAM_SALON_CHAT_ID
    if not salon_chat_id:
        return

    welcome_text = (
        "🤖 *Бот запущен!*\n\n"
        "📋 *Доступные команды:*\n\n"
        "👁 *Просмотр записей:*\n"
        "/today — записи на сегодня\n"
        "/tomorrow — записи на завтра\n"
        "/week — записи на неделю\n\n"
        "⏰ *Свободные слоты:*\n"
        "/slots — слоты на сегодня\n"
        "/slots 15.02 — слоты на дату\n\n"
        "✏️ *Ручная запись:*\n"
        "/add — записать клиента вручную\n\n"
        "💅 *Услуги:*\n"
        "/services — список услуг\n\n"
        "ℹ️ Новые записи будут приходить автоматически с кнопками подтверждения."
    )

    try:
        await application.bot.send_message(
            chat_id=salon_chat_id,
            text=welcome_text,
            parse_mode="Markdown"
        )
        print(f"✅ Инструкция отправлена специалисту (chat_id: {salon_chat_id})")
    except Exception as e:
        print(f"⚠️ Не удалось отправить инструкцию: {e}")


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Обработчик записи (ConversationHandler)
    booking_conv = ConversationHandler(
        entry_points=[CommandHandler("book", book_start)],
        states={
            SELECTING_SERVICE: [CallbackQueryHandler(service_selected, pattern="^service_")],
            SELECTING_DATE: [CallbackQueryHandler(date_selected, pattern="^date_")],
            SELECTING_TIME: [CallbackQueryHandler(time_selected, pattern="^time_")],
            ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_entered)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_entered)],
            CONFIRMING: [CallbackQueryHandler(confirm_booking, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("services", services_list))
    application.add_handler(CommandHandler("myappointments", my_appointments))
    application.add_handler(booking_conv)

    # Команды для специалиста
    application.add_handler(CommandHandler("today", today_appointments))
    application.add_handler(CommandHandler("tomorrow", tomorrow_appointments))
    application.add_handler(CommandHandler("week", week_appointments))
    application.add_handler(CommandHandler("slots", available_slots))

    # Ручная запись клиента (для специалиста)
    manual_booking_conv = ConversationHandler(
        entry_points=[CommandHandler("add", manual_add_start)],
        states={
            MANUAL_SERVICE: [CallbackQueryHandler(manual_service_selected, pattern="^madd_")],
            MANUAL_DATE: [CallbackQueryHandler(manual_date_selected, pattern="^madd_")],
            MANUAL_TIME: [CallbackQueryHandler(manual_time_selected, pattern="^madd_")],
            MANUAL_CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_client_name)],
            MANUAL_CLIENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_client_phone)],
            MANUAL_CONFIRM: [CallbackQueryHandler(manual_confirm, pattern="^madd_")],
        },
        fallbacks=[CommandHandler("cancel", manual_cancel)],
    )
    application.add_handler(manual_booking_conv)

    # Отправляем инструкцию специалисту при запуске
    application.post_init = send_specialist_welcome

    # Запускаем бота
    print("🤖 Telegram бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
