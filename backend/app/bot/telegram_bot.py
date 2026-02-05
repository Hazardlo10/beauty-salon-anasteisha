"""
Telegram бот для специалиста (ПРИВАТНЫЙ)
Только для управления записями - клиенты записываются через сайт!
"""
import os
import sys
import logging
from datetime import datetime, timedelta, date, time as dt_time
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
from app.models.blocked_slot import BlockedSlot
from app.models.work_schedule import WorkSchedule
from app.models.master_availability import MasterAvailability
from app.models.review import Review
from app.services.schedule import ScheduleService
from app.config import get_settings

settings = get_settings()

# Состояния разговора для клиентов (НЕ ИСПОЛЬЗУЕТСЯ - бот только для специалиста)
# SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, ENTERING_PHONE, ENTERING_NAME, CONFIRMING = range(6)

# Состояния для ручной записи специалистом
MANUAL_SERVICE, MANUAL_DATE, MANUAL_TIME, MANUAL_CLIENT_NAME, MANUAL_CLIENT_PHONE, MANUAL_CONFIRM = range(100, 106)

# Состояния для редактирования услуг
EDIT_SELECT_SERVICE, EDIT_SELECT_ACTION, EDIT_ENTER_VALUE = range(200, 203)

# Состояния для управления слотами
BLOCK_SELECT_DATE, BLOCK_SELECT_TIME, BLOCK_SELECT_DURATION, BLOCK_ENTER_REASON = range(300, 304)
UNBLOCK_SELECT_DATE, UNBLOCK_SELECT_SLOT = range(350, 352)

# Состояния для управления расписанием
SCHEDULE_SELECT_DAY, SCHEDULE_SELECT_ACTION, SCHEDULE_ENTER_TIME = range(400, 403)

# Состояния для персонального расписания мастера
MYSCHEDULE_SELECT_DAY, MYSCHEDULE_SELECT_ACTION, MYSCHEDULE_ENTER_TIME = range(450, 453)


def get_db() -> Session:
    """Получить сессию базы данных"""
    return SessionLocal()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие (ТОЛЬКО ДЛЯ СПЕЦИАЛИСТА)"""
    user = update.effective_user
    telegram_id = user.id

    logger.info(f"Команда /start от пользователя {telegram_id} ({user.first_name})")

    # Проверяем, является ли пользователь специалистом
    if not is_specialist(telegram_id):
        logger.info(f"Пользователь {telegram_id} НЕ является специалистом")
        await update.message.reply_text(
            "🔒 <b>Этот бот только для специалиста.</b>\n\n"
            "Для записи на прием посетите наш сайт:\n"
            "🌐 anasteisha.ru",
            parse_mode="HTML"
        )
        return

    logger.info(f"Пользователь {telegram_id} является специалистом, отправляем меню команд")

    # Приветствие для специалиста
    welcome_text = (
        "Здравствуйте! 👩‍⚕️\n\n"
        "<b>Команды для управления записями:</b>\n"
        "/today - 📅 Записи на сегодня\n"
        "/tomorrow - 📆 Записи на завтра\n"
        "/week - 🗓 Записи на неделю\n"
        "/slots - ⏰ Свободные слоты\n"
        "/add - ✏️ Записать клиента вручную\n"
        "/reminders - 📬 Отправить напоминания\n\n"
        "<b>Ваше расписание:</b>\n"
        "/myschedule - 👩‍⚕️ Моё расписание\n"
        "/block - 🚫 Заблокировать слот\n"
        "/unblock - ✅ Разблокировать слот\n"
        "/schedule - 📅 Часы работы салона\n\n"
        "<b>Управление услугами:</b>\n"
        "/services - 💅 Список услуг\n"
        "/edit - ✏️ Изменить цену/название\n\n"
        "<b>Отзывы:</b>\n"
        "/reviews - 💬 Отзывы на модерации\n"
    )

    await update.message.reply_text(welcome_text, parse_mode="HTML")


async def services_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /services - список всех услуг (только для специалиста)"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Этот бот только для специалиста.")
        return

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


async def pending_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reviews - показать неопубликованные отзывы"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
        return

    db = get_db()
    try:
        reviews = db.query(Review).filter(Review.is_published == False).order_by(Review.created_at.desc()).all()

        if not reviews:
            await update.message.reply_text("✅ Нет отзывов, ожидающих модерации.")
            return

        for review in reviews[:5]:  # Показываем максимум 5 последних
            stars = "⭐" * review.rating + "☆" * (5 - review.rating)
            created = review.created_at.strftime("%d.%m.%Y") if review.created_at else "—"

            text = (
                f"💬 <b>ОТЗЫВ #{review.id}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"{stars}  <b>({review.rating}/5)</b>\n\n"
                f"👤 <b>Клиент:</b> {review.name}\n"
                f"💆 <b>Услуга:</b> {review.service or '—'}\n\n"
                f"📝 <b>Текст:</b>\n"
                f"<i>\"{review.text}\"</i>\n\n"
                f"🕐 {created}"
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Опубликовать", callback_data=f"review_approve_{review.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"review_reject_{review.id}")
                ]
            ])

            await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

        if len(reviews) > 5:
            await update.message.reply_text(f"<i>Показаны последние 5 из {len(reviews)} отзывов</i>", parse_mode="HTML")

    finally:
        db.close()


async def review_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок модерации отзывов"""
    query = update.callback_query
    await query.answer()

    if not is_specialist(update.effective_user.id):
        await query.edit_message_text("🔒 Только для специалиста.")
        return

    data = query.data
    db = get_db()
    try:
        if data.startswith("review_approve_"):
            review_id = int(data.replace("review_approve_", ""))
            review = db.query(Review).filter(Review.id == review_id).first()

            if not review:
                await query.edit_message_text("❌ Отзыв не найден.")
                return

            review.is_published = True
            db.commit()

            text_preview = f"{review.text[:100]}..." if len(review.text) > 100 else review.text
            await query.edit_message_text(
                f"✅ <b>Отзыв #{review_id} опубликован!</b>\n\n"
                f"👤 {review.name}\n"
                f"⭐ {review.rating}/5\n"
                f"💬 <i>\"{text_preview}\"</i>",
                parse_mode="HTML"
            )

        elif data.startswith("review_reject_"):
            review_id = int(data.replace("review_reject_", ""))
            review = db.query(Review).filter(Review.id == review_id).first()

            if not review:
                await query.edit_message_text("❌ Отзыв не найден.")
                return

            # Удаляем отзыв
            db.delete(review)
            db.commit()

            await query.edit_message_text(
                f"🗑 <b>Отзыв #{review_id} отклонён и удалён.</b>",
                parse_mode="HTML"
            )

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


async def send_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reminders - отправить напоминания о записях на завтра"""
    from ..services.notifications import notify_client_reminder

    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("❌ Эта команда доступна только для специалиста.")
        return

    db = get_db()
    tomorrow = date.today() + timedelta(days=1)
    sent_count = 0

    try:
        # Находим все подтверждённые записи на завтра
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date == tomorrow,
            Appointment.status == "confirmed"
        ).all()

        if not appointments:
            await update.message.reply_text(
                f"📅 На завтра ({tomorrow.strftime('%d.%m.%Y')}) нет подтверждённых записей."
            )
            return

        await update.message.reply_text(f"⏳ Отправляю напоминания ({len(appointments)} записей)...")

        for apt in appointments:
            client = db.query(Client).filter(Client.id == apt.client_id).first()
            service = db.query(Service).filter(Service.id == apt.service_id).first()

            if not client or not service:
                continue

            # Отправляем напоминание
            await notify_client_reminder(
                client_email=client.email,
                client_telegram_id=client.telegram_id,
                client_name=client.name,
                client_phone=client.phone,
                service_name=service.name,
                appointment_date=apt.appointment_date,
                appointment_time=apt.appointment_time.strftime("%H:%M"),
                appointment_id=apt.id
            )
            sent_count += 1

        await update.message.reply_text(
            f"✅ *Напоминания отправлены!*\n\n"
            f"📅 Дата: {tomorrow.strftime('%d.%m.%Y')}\n"
            f"📬 Отправлено: {sent_count} из {len(appointments)}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
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


# ==================== РЕДАКТИРОВАНИЕ УСЛУГ ====================

async def edit_services_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /edit - начать редактирование услуг"""
    user_id = update.effective_user.id

    if not is_specialist(user_id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
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
                    callback_data=f"edit_svc_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "✏️ *Редактирование услуг*\n\n"
            "Выберите услугу для редактирования:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return EDIT_SELECT_SERVICE
    finally:
        db.close()


async def edit_service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор услуги для редактирования"""
    query = update.callback_query
    await query.answer()

    if query.data == "edit_cancel":
        await query.edit_message_text("Редактирование отменено.")
        return ConversationHandler.END

    service_id = int(query.data.split("_")[2])
    context.user_data["edit_service_id"] = service_id

    db = get_db()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            await query.edit_message_text("❌ Услуга не найдена.")
            return ConversationHandler.END

        context.user_data["edit_service_name"] = service.name
        context.user_data["edit_service_price"] = float(service.price)

        keyboard = [
            [InlineKeyboardButton("💰 Изменить цену", callback_data="edit_action_price")],
            [InlineKeyboardButton("📝 Изменить название", callback_data="edit_action_name")],
            [InlineKeyboardButton("📄 Изменить описание", callback_data="edit_action_desc")],
            [InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✏️ *Редактирование услуги:*\n\n"
            f"📌 *{service.name}*\n"
            f"💰 Цена: {service.price} ₽\n"
            f"⏱ Длительность: {service.duration_minutes} мин\n"
            f"📝 Описание: {service.description or 'не указано'}\n\n"
            "Что вы хотите изменить?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return EDIT_SELECT_ACTION
    finally:
        db.close()


async def edit_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор действия (что редактируем)"""
    query = update.callback_query
    await query.answer()

    if query.data == "edit_cancel":
        await query.edit_message_text("Редактирование отменено.")
        return ConversationHandler.END

    action = query.data.split("_")[2]  # price, name, desc
    context.user_data["edit_action"] = action

    service_name = context.user_data["edit_service_name"]
    service_price = context.user_data["edit_service_price"]

    if action == "price":
        await query.edit_message_text(
            f"💰 *Изменение цены*\n\n"
            f"Услуга: *{service_name}*\n"
            f"Текущая цена: *{service_price}* ₽\n\n"
            "Введите новую цену (только число):",
            parse_mode="Markdown"
        )
    elif action == "name":
        await query.edit_message_text(
            f"📝 *Изменение названия*\n\n"
            f"Текущее название: *{service_name}*\n\n"
            "Введите новое название:",
            parse_mode="Markdown"
        )
    elif action == "desc":
        await query.edit_message_text(
            f"📄 *Изменение описания*\n\n"
            f"Услуга: *{service_name}*\n\n"
            "Введите новое описание (или '-' чтобы удалить):",
            parse_mode="Markdown"
        )

    return EDIT_ENTER_VALUE


async def edit_enter_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод нового значения"""
    value = update.message.text.strip()
    action = context.user_data.get("edit_action")
    service_id = context.user_data.get("edit_service_id")

    db = get_db()
    try:
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            await update.message.reply_text("❌ Услуга не найдена.")
            return ConversationHandler.END

        old_value = None
        new_value = value

        if action == "price":
            try:
                new_price = float(value.replace(",", ".").replace(" ", ""))
                if new_price <= 0:
                    raise ValueError("Цена должна быть больше 0")
                old_value = f"{service.price} ₽"
                service.price = new_price
                new_value = f"{new_price} ₽"
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат цены. Введите число (например: 2500):"
                )
                return EDIT_ENTER_VALUE

        elif action == "name":
            if len(value) < 3:
                await update.message.reply_text(
                    "❌ Название слишком короткое. Минимум 3 символа:"
                )
                return EDIT_ENTER_VALUE
            old_value = service.name
            service.name = value

        elif action == "desc":
            old_value = service.description or "пусто"
            if value == "-":
                service.description = None
                new_value = "удалено"
            else:
                service.description = value

        db.commit()

        action_names = {"price": "Цена", "name": "Название", "desc": "Описание"}

        await update.message.reply_text(
            f"✅ *Услуга обновлена!*\n\n"
            f"📌 {service.name}\n"
            f"🔄 {action_names[action]}:\n"
            f"   Было: {old_value}\n"
            f"   Стало: {new_value}\n\n"
            "Используйте /edit для дальнейшего редактирования.",
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при сохранении: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования"""
    await update.message.reply_text("Редактирование отменено.")
    return ConversationHandler.END


# ==================== БЛОКИРОВКА СЛОТОВ ====================

async def block_slot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /block - начать блокировку слота"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
        return ConversationHandler.END

    # Генерируем даты на ближайшие 14 дней
    keyboard = []
    today = date.today()
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    month_names = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

    row = []
    for i in range(14):
        d = today + timedelta(days=i)
        day_name = day_names[d.weekday()]
        label = f"{d.day} {month_names[d.month-1]}, {day_name}"
        callback = f"block_date_{d.isoformat()}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="block_cancel")])

    await update.message.reply_text(
        "🚫 *Блокировка слота*\n\n"
        "Выберите дату:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return BLOCK_SELECT_DATE


async def block_date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты для блокировки"""
    query = update.callback_query
    await query.answer()

    if query.data == "block_cancel":
        await query.edit_message_text("Блокировка отменена.")
        return ConversationHandler.END

    date_str = query.data.split("_")[2]
    selected_date = date.fromisoformat(date_str)
    context.user_data["block_date"] = selected_date

    # Получаем рабочие часы на эту дату
    db = get_db()
    try:
        schedule_service = ScheduleService(db)
        working = schedule_service.get_working_hours(selected_date)

        if not working or not working["is_working_day"]:
            await query.edit_message_text("❌ Это выходной день, блокировать нечего.")
            return ConversationHandler.END

        # Генерируем все слоты рабочего дня
        all_slots = schedule_service.generate_time_slots(
            working["start_time"],
            working["end_time"]
        )

        # Получаем уже заблокированные
        blocked = schedule_service.get_blocked_slots(selected_date)
        blocked_times = {b["time"] for b in blocked}

        # Фильтруем только доступные для блокировки
        available_slots = [s for s in all_slots if s not in blocked_times]

        if not available_slots:
            await query.edit_message_text("❌ Все слоты на эту дату уже заблокированы.")
            return ConversationHandler.END

        keyboard = []
        row = []
        for slot in available_slots:
            label = slot.strftime("%H:%M")
            callback = f"block_time_{label}"
            row.append(InlineKeyboardButton(label, callback_data=callback))
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Кнопка "Заблокировать весь день"
        keyboard.append([InlineKeyboardButton("🚫 Весь день", callback_data="block_time_allday")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="block_cancel")])

        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        month_names = ["января", "февраля", "марта", "апреля", "мая", "июня",
                      "июля", "августа", "сентября", "октября", "ноября", "декабря"]

        await query.edit_message_text(
            f"🚫 *Блокировка слота*\n\n"
            f"📅 {selected_date.day} {month_names[selected_date.month-1]}, {day_names[selected_date.weekday()]}\n\n"
            "Выберите время для блокировки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return BLOCK_SELECT_TIME

    finally:
        db.close()


async def block_time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени для блокировки"""
    query = update.callback_query
    await query.answer()

    if query.data == "block_cancel":
        await query.edit_message_text("Блокировка отменена.")
        return ConversationHandler.END

    time_str = query.data.split("_")[2]
    context.user_data["block_time"] = time_str

    if time_str == "allday":
        # Блокируем весь день
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="block_dur_allday")],
            [InlineKeyboardButton("❌ Отмена", callback_data="block_cancel")]
        ]
        await query.edit_message_text(
            "🚫 *Блокировка всего дня*\n\n"
            "Все свободные слоты будут заблокированы.\n"
            "Подтвердите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        # Выбираем длительность
        keyboard = [
            [
                InlineKeyboardButton("30 мин", callback_data="block_dur_30"),
                InlineKeyboardButton("1 час", callback_data="block_dur_60"),
            ],
            [
                InlineKeyboardButton("1.5 часа", callback_data="block_dur_90"),
                InlineKeyboardButton("2 часа", callback_data="block_dur_120"),
            ],
            [
                InlineKeyboardButton("3 часа", callback_data="block_dur_180"),
                InlineKeyboardButton("4 часа", callback_data="block_dur_240"),
            ],
            [InlineKeyboardButton("❌ Отмена", callback_data="block_cancel")]
        ]
        await query.edit_message_text(
            f"🚫 *Блокировка с {time_str}*\n\n"
            "Выберите длительность:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    return BLOCK_SELECT_DURATION


async def block_duration_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор длительности и подтверждение блокировки"""
    query = update.callback_query
    await query.answer()

    if query.data == "block_cancel":
        await query.edit_message_text("Блокировка отменена.")
        return ConversationHandler.END

    selected_date = context.user_data.get("block_date")
    time_str = context.user_data.get("block_time")
    dur_str = query.data.split("_")[2]

    db = get_db()
    try:
        schedule_service = ScheduleService(db)

        if dur_str == "allday":
            # Блокируем весь день - все свободные слоты
            working = schedule_service.get_working_hours(selected_date)
            all_slots = schedule_service.generate_time_slots(
                working["start_time"],
                working["end_time"]
            )
            blocked = schedule_service.get_blocked_slots(selected_date)
            blocked_times = {b["time"] for b in blocked}
            available_slots = [s for s in all_slots if s not in blocked_times]

            count = 0
            for slot in available_slots:
                schedule_service.block_slot(selected_date, slot, 30, "Выходной")
                count += 1

            await query.edit_message_text(
                f"✅ *День заблокирован!*\n\n"
                f"📅 {selected_date.strftime('%d.%m.%Y')}\n"
                f"🚫 Заблокировано слотов: {count}\n\n"
                "Используйте /unblock для разблокировки.",
                parse_mode="Markdown"
            )
        else:
            duration = int(dur_str)
            slot_time = datetime.strptime(time_str, "%H:%M").time()

            # Блокируем все слоты в указанном диапазоне
            slots_to_block = duration // 30
            current_time = datetime.combine(date.today(), slot_time)

            count = 0
            for i in range(slots_to_block):
                t = current_time.time()
                try:
                    schedule_service.block_slot(selected_date, t, 30, "Занято")
                    count += 1
                except:
                    pass  # Слот уже заблокирован
                current_time += timedelta(minutes=30)

            end_time = (datetime.combine(date.today(), slot_time) + timedelta(minutes=duration)).time()

            await query.edit_message_text(
                f"✅ *Слот заблокирован!*\n\n"
                f"📅 {selected_date.strftime('%d.%m.%Y')}\n"
                f"⏰ {time_str} — {end_time.strftime('%H:%M')}\n"
                f"🚫 Заблокировано: {count} слот(ов)\n\n"
                "Используйте /unblock для разблокировки.",
                parse_mode="Markdown"
            )

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def block_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена блокировки"""
    await update.message.reply_text("Блокировка отменена.")
    return ConversationHandler.END


# ==================== РАЗБЛОКИРОВКА СЛОТОВ ====================

async def unblock_slot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unblock - разблокировать слоты"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
        return ConversationHandler.END

    db = get_db()
    try:
        # Находим все заблокированные слоты на будущие даты
        today = date.today()
        blocked_slots = db.query(BlockedSlot).filter(
            BlockedSlot.slot_date >= today
        ).order_by(BlockedSlot.slot_date, BlockedSlot.slot_time).all()

        if not blocked_slots:
            await update.message.reply_text(
                "✅ Нет заблокированных слотов.\n\n"
                "Используйте /block чтобы заблокировать время."
            )
            return ConversationHandler.END

        # Группируем по датам
        dates = {}
        for slot in blocked_slots:
            if slot.slot_date not in dates:
                dates[slot.slot_date] = []
            dates[slot.slot_date].append(slot)

        keyboard = []
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        month_names = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

        for d, slots in dates.items():
            day_name = day_names[d.weekday()]
            label = f"{d.day} {month_names[d.month-1]}, {day_name} ({len(slots)} слотов)"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"unblock_date_{d.isoformat()}")])

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="unblock_cancel")])

        await update.message.reply_text(
            "✅ *Разблокировка слотов*\n\n"
            "Выберите дату:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return UNBLOCK_SELECT_DATE

    finally:
        db.close()


async def unblock_date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты для разблокировки"""
    query = update.callback_query
    await query.answer()

    if query.data == "unblock_cancel":
        await query.edit_message_text("Разблокировка отменена.")
        return ConversationHandler.END

    date_str = query.data.split("_")[2]
    selected_date = date.fromisoformat(date_str)
    context.user_data["unblock_date"] = selected_date

    db = get_db()
    try:
        blocked_slots = db.query(BlockedSlot).filter(
            BlockedSlot.slot_date == selected_date
        ).order_by(BlockedSlot.slot_time).all()

        if not blocked_slots:
            await query.edit_message_text("На эту дату нет заблокированных слотов.")
            return ConversationHandler.END

        keyboard = []
        row = []
        for slot in blocked_slots:
            label = slot.slot_time.strftime("%H:%M")
            callback = f"unblock_slot_{slot.id}"
            row.append(InlineKeyboardButton(label, callback_data=callback))
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Кнопка "Разблокировать всё"
        keyboard.append([InlineKeyboardButton("✅ Разблокировать всё", callback_data="unblock_slot_all")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="unblock_cancel")])

        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        month_names = ["января", "февраля", "марта", "апреля", "мая", "июня",
                      "июля", "августа", "сентября", "октября", "ноября", "декабря"]

        await query.edit_message_text(
            f"✅ *Разблокировка слотов*\n\n"
            f"📅 {selected_date.day} {month_names[selected_date.month-1]}, {day_names[selected_date.weekday()]}\n"
            f"🚫 Заблокировано: {len(blocked_slots)} слотов\n\n"
            "Выберите слот для разблокировки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return UNBLOCK_SELECT_SLOT

    finally:
        db.close()


async def unblock_slot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разблокировка выбранного слота"""
    query = update.callback_query
    await query.answer()

    if query.data == "unblock_cancel":
        await query.edit_message_text("Разблокировка отменена.")
        return ConversationHandler.END

    selected_date = context.user_data.get("unblock_date")
    slot_id = query.data.split("_")[2]

    db = get_db()
    try:
        if slot_id == "all":
            # Разблокировать все
            deleted = db.query(BlockedSlot).filter(
                BlockedSlot.slot_date == selected_date
            ).delete()
            db.commit()

            await query.edit_message_text(
                f"✅ *Все слоты разблокированы!*\n\n"
                f"📅 {selected_date.strftime('%d.%m.%Y')}\n"
                f"Разблокировано: {deleted} слотов",
                parse_mode="Markdown"
            )
        else:
            slot = db.query(BlockedSlot).filter(BlockedSlot.id == int(slot_id)).first()
            if slot:
                time_str = slot.slot_time.strftime("%H:%M")
                db.delete(slot)
                db.commit()

                await query.edit_message_text(
                    f"✅ *Слот разблокирован!*\n\n"
                    f"📅 {selected_date.strftime('%d.%m.%Y')}\n"
                    f"⏰ {time_str}",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("❌ Слот не найден.")

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def unblock_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена разблокировки"""
    await update.message.reply_text("Разблокировка отменена.")
    return ConversationHandler.END


# ==================== УПРАВЛЕНИЕ РАСПИСАНИЕМ ====================

async def schedule_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /schedule - управление рабочими часами"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
        return ConversationHandler.END

    db = get_db()
    try:
        schedules = db.query(WorkSchedule).order_by(WorkSchedule.day_of_week).all()
        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        text = "📅 *Рабочее расписание:*\n\n"
        keyboard = []

        for schedule in schedules:
            day = day_names[schedule.day_of_week]
            if schedule.is_working_day:
                status = f"{schedule.start_time.strftime('%H:%M')}—{schedule.end_time.strftime('%H:%M')}"
            else:
                status = "Выходной"
            text += f"*{day}:* {status}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{day[:2]}: {status}",
                    callback_data=f"sched_day_{schedule.day_of_week}"
                )
            ])

        keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="sched_cancel")])

        text += "\nВыберите день для изменения:"

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return SCHEDULE_SELECT_DAY

    finally:
        db.close()


async def schedule_day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дня для изменения расписания"""
    query = update.callback_query
    await query.answer()

    if query.data == "sched_cancel":
        await query.edit_message_text("Закрыто.")
        return ConversationHandler.END

    day_of_week = int(query.data.split("_")[2])
    context.user_data["sched_day"] = day_of_week

    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    db = get_db()
    try:
        schedule = db.query(WorkSchedule).filter(WorkSchedule.day_of_week == day_of_week).first()

        if schedule and schedule.is_working_day:
            current = f"{schedule.start_time.strftime('%H:%M')}—{schedule.end_time.strftime('%H:%M')}"
        else:
            current = "Выходной"

        keyboard = [
            [InlineKeyboardButton("🕐 10:00—18:00", callback_data="sched_set_10:00-18:00")],
            [InlineKeyboardButton("🕐 10:00—20:00", callback_data="sched_set_10:00-20:00")],
            [InlineKeyboardButton("🕐 09:00—18:00", callback_data="sched_set_09:00-18:00")],
            [InlineKeyboardButton("🕐 09:00—21:00", callback_data="sched_set_09:00-21:00")],
            [InlineKeyboardButton("📝 Ввести вручную", callback_data="sched_set_custom")],
            [InlineKeyboardButton("🚫 Сделать выходным", callback_data="sched_set_dayoff")],
            [InlineKeyboardButton("❌ Отмена", callback_data="sched_cancel")]
        ]

        await query.edit_message_text(
            f"📅 *{day_names[day_of_week]}*\n\n"
            f"Текущее: *{current}*\n\n"
            "Выберите новое расписание:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return SCHEDULE_SELECT_ACTION

    finally:
        db.close()


async def schedule_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор нового расписания"""
    query = update.callback_query
    await query.answer()

    if query.data == "sched_cancel":
        await query.edit_message_text("Изменение отменено.")
        return ConversationHandler.END

    day_of_week = context.user_data.get("sched_day")
    action = query.data.split("_")[2]
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    if action == "custom":
        await query.edit_message_text(
            f"📅 *{day_names[day_of_week]}*\n\n"
            "Введите время работы в формате:\n"
            "`ЧЧ:ММ-ЧЧ:ММ`\n\n"
            "Например: `09:00-18:00`",
            parse_mode="Markdown"
        )
        return SCHEDULE_ENTER_TIME

    db = get_db()
    try:
        schedule = db.query(WorkSchedule).filter(WorkSchedule.day_of_week == day_of_week).first()

        if action == "dayoff":
            if schedule:
                schedule.is_working_day = False
            result = "🚫 Выходной"
        else:
            times = action.split("-")
            start = datetime.strptime(times[0], "%H:%M").time()
            end = datetime.strptime(times[1], "%H:%M").time()

            if schedule:
                schedule.start_time = start
                schedule.end_time = end
                schedule.is_working_day = True
            else:
                schedule = WorkSchedule(
                    day_of_week=day_of_week,
                    start_time=start,
                    end_time=end,
                    is_working_day=True
                )
                db.add(schedule)

            result = f"⏰ {times[0]}—{times[1]}"

        db.commit()

        await query.edit_message_text(
            f"✅ *Расписание обновлено!*\n\n"
            f"📅 {day_names[day_of_week]}: {result}",
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def schedule_enter_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени вручную"""
    text = update.message.text.strip()
    day_of_week = context.user_data.get("sched_day")
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    try:
        parts = text.replace(" ", "").split("-")
        if len(parts) != 2:
            raise ValueError("Неверный формат")

        start = datetime.strptime(parts[0], "%H:%M").time()
        end = datetime.strptime(parts[1], "%H:%M").time()

        if start >= end:
            raise ValueError("Время начала должно быть раньше окончания")

        db = get_db()
        try:
            schedule = db.query(WorkSchedule).filter(WorkSchedule.day_of_week == day_of_week).first()

            if schedule:
                schedule.start_time = start
                schedule.end_time = end
                schedule.is_working_day = True
            else:
                schedule = WorkSchedule(
                    day_of_week=day_of_week,
                    start_time=start,
                    end_time=end,
                    is_working_day=True
                )
                db.add(schedule)

            db.commit()

            await update.message.reply_text(
                f"✅ *Расписание обновлено!*\n\n"
                f"📅 {day_names[day_of_week]}: ⏰ {start.strftime('%H:%M')}—{end.strftime('%H:%M')}",
                parse_mode="Markdown"
            )

            return ConversationHandler.END

        finally:
            db.close()

    except ValueError as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\n"
            "Введите время в формате `ЧЧ:ММ-ЧЧ:ММ`\n"
            "Например: `09:00-18:00`",
            parse_mode="Markdown"
        )
        return SCHEDULE_ENTER_TIME


async def schedule_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена изменения расписания"""
    await update.message.reply_text("Изменение расписания отменено.")
    return ConversationHandler.END


# ==================== ПЕРСОНАЛЬНОЕ РАСПИСАНИЕ МАСТЕРА ====================

async def myschedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myschedule - управление персональным расписанием мастера"""
    if not is_specialist(update.effective_user.id):
        await update.message.reply_text("🔒 Эта команда доступна только для специалиста.")
        return ConversationHandler.END

    db = get_db()
    try:
        schedule_service = ScheduleService(db)
        week_schedule = schedule_service.get_master_week_schedule()

        text = "👩‍⚕️ *Моё расписание:*\n\n"
        text += "_Время, когда вы принимаете клиентов:_\n\n"

        keyboard = []
        for day in week_schedule:
            if day["is_available"]:
                status = f"✅ {day['start_time']}—{day['end_time']}"
            else:
                status = "❌ Выходной"

            text += f"*{day['day_name']}:* {status}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{day['day_name']}: {status}",
                    callback_data=f"mysched_day_{day['day_of_week']}"
                )
            ])

        keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="mysched_cancel")])

        text += "\n💡 _Выберите день, чтобы изменить своё расписание._\n"
        text += "_Клиенты смогут записаться только в это время._"

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return MYSCHEDULE_SELECT_DAY

    finally:
        db.close()


async def myschedule_day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дня для изменения персонального расписания"""
    query = update.callback_query
    await query.answer()

    if query.data == "mysched_cancel":
        await query.edit_message_text("Закрыто.")
        return ConversationHandler.END

    day_of_week = int(query.data.split("_")[2])
    context.user_data["mysched_day"] = day_of_week

    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    db = get_db()
    try:
        schedule_service = ScheduleService(db)
        master_hours = schedule_service.get_master_availability(date.today() + timedelta(days=(day_of_week - date.today().weekday()) % 7))

        if master_hours and master_hours["is_available"]:
            current = f"{master_hours['start_time'].strftime('%H:%M')}—{master_hours['end_time'].strftime('%H:%M')}"
        else:
            current = "Выходной"

        # Получаем часы работы салона для этого дня
        salon_hours = schedule_service.get_working_hours(date.today() + timedelta(days=(day_of_week - date.today().weekday()) % 7))
        if salon_hours and salon_hours["is_working_day"]:
            salon_info = f"Салон: {salon_hours['start_time'].strftime('%H:%M')}—{salon_hours['end_time'].strftime('%H:%M')}"
        else:
            salon_info = "Салон: выходной"

        keyboard = [
            [InlineKeyboardButton("🕐 10:00—14:00 (утро)", callback_data="mysched_set_10:00-14:00")],
            [InlineKeyboardButton("🕐 14:00—18:00 (день)", callback_data="mysched_set_14:00-18:00")],
            [InlineKeyboardButton("🕐 14:00—20:00 (вечер)", callback_data="mysched_set_14:00-20:00")],
            [InlineKeyboardButton("🕐 10:00—18:00 (сокращ.)", callback_data="mysched_set_10:00-18:00")],
            [InlineKeyboardButton("🕐 10:00—20:00 (полный)", callback_data="mysched_set_10:00-20:00")],
            [InlineKeyboardButton("📝 Ввести вручную", callback_data="mysched_set_custom")],
            [InlineKeyboardButton("🚫 Не принимаю", callback_data="mysched_set_dayoff")],
            [InlineKeyboardButton("❌ Отмена", callback_data="mysched_cancel")]
        ]

        await query.edit_message_text(
            f"👩‍⚕️ *{day_names[day_of_week]}*\n\n"
            f"📌 Сейчас: *{current}*\n"
            f"🏠 {salon_info}\n\n"
            "Когда вы готовы принимать клиентов?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return MYSCHEDULE_SELECT_ACTION

    finally:
        db.close()


async def myschedule_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор нового расписания мастера"""
    query = update.callback_query
    await query.answer()

    if query.data == "mysched_cancel":
        await query.edit_message_text("Изменение отменено.")
        return ConversationHandler.END

    day_of_week = context.user_data.get("mysched_day")
    action = query.data.split("_")[2]
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    if action == "custom":
        await query.edit_message_text(
            f"👩‍⚕️ *{day_names[day_of_week]}*\n\n"
            "Введите ваше время работы:\n"
            "`ЧЧ:ММ-ЧЧ:ММ`\n\n"
            "Например: `11:00-17:00`",
            parse_mode="Markdown"
        )
        return MYSCHEDULE_ENTER_TIME

    db = get_db()
    try:
        schedule_service = ScheduleService(db)

        if action == "dayoff":
            schedule_service.toggle_master_day(day_of_week, False)
            result = "❌ Не принимаю"
        else:
            times = action.split("-")
            start = datetime.strptime(times[0], "%H:%M").time()
            end = datetime.strptime(times[1], "%H:%M").time()

            schedule_service.set_master_availability(day_of_week, start, end, True)
            result = f"✅ {times[0]}—{times[1]}"

        await query.edit_message_text(
            f"✅ *Расписание обновлено!*\n\n"
            f"📅 {day_names[day_of_week]}: {result}\n\n"
            "_Клиенты увидят только доступные слоты._",
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def myschedule_enter_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени мастера вручную"""
    text = update.message.text.strip()
    day_of_week = context.user_data.get("mysched_day")
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    try:
        parts = text.replace(" ", "").split("-")
        if len(parts) != 2:
            raise ValueError("Неверный формат")

        start = datetime.strptime(parts[0], "%H:%M").time()
        end = datetime.strptime(parts[1], "%H:%M").time()

        if start >= end:
            raise ValueError("Время начала должно быть раньше окончания")

        db = get_db()
        try:
            schedule_service = ScheduleService(db)
            schedule_service.set_master_availability(day_of_week, start, end, True)

            await update.message.reply_text(
                f"✅ *Расписание обновлено!*\n\n"
                f"📅 {day_names[day_of_week]}: ✅ {start.strftime('%H:%M')}—{end.strftime('%H:%M')}\n\n"
                "_Клиенты увидят только доступные слоты._",
                parse_mode="Markdown"
            )

            return ConversationHandler.END

        finally:
            db.close()

    except ValueError as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n\n"
            "Введите время в формате `ЧЧ:ММ-ЧЧ:ММ`\n"
            "Например: `11:00-17:00`",
            parse_mode="Markdown"
        )
        return MYSCHEDULE_ENTER_TIME


async def myschedule_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена изменения расписания мастера"""
    await update.message.reply_text("Изменение расписания отменено.")
    return ConversationHandler.END


async def send_specialist_welcome(application):
    """Отправить инструкцию специалисту при запуске бота"""
    salon_chat_id = settings.TELEGRAM_SALON_CHAT_ID
    if not salon_chat_id:
        return

    welcome_text = (
        "🤖 *Бот запущен!* (приватный режим)\n\n"
        "📋 *Доступные команды:*\n\n"
        "👁 *Просмотр записей:*\n"
        "/today — записи на сегодня\n"
        "/tomorrow — записи на завтра\n"
        "/week — записи на неделю\n\n"
        "👩‍⚕️ *Ваше расписание:*\n"
        "/myschedule — моё расписание\n"
        "/slots — слоты на сегодня\n"
        "/block — заблокировать время\n"
        "/unblock — разблокировать время\n\n"
        "✏️ *Ручная запись:*\n"
        "/add — записать клиента вручную\n\n"
        "💅 *Управление услугами:*\n"
        "/services — список услуг\n"
        "/edit — изменить цену/название\n\n"
        "ℹ️ Новые записи с сайта будут приходить автоматически.\n"
        "🔒 Бот доступен только вам."
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


async def unauthorized_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для неавторизованных пользователей"""
    if update.message and not is_specialist(update.effective_user.id):
        await update.message.reply_text(
            "🔒 *Этот бот только для специалиста.*\n\n"
            "Для записи на прием посетите наш сайт:\n"
            "🌐 anasteisha.ru",
            parse_mode="Markdown"
        )


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчики (только для специалиста)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("services", services_list))

    # Команды для специалиста
    application.add_handler(CommandHandler("today", today_appointments))
    application.add_handler(CommandHandler("tomorrow", tomorrow_appointments))
    application.add_handler(CommandHandler("week", week_appointments))
    application.add_handler(CommandHandler("slots", available_slots))
    application.add_handler(CommandHandler("reminders", send_reminders))
    application.add_handler(CommandHandler("reviews", pending_reviews))

    # Обработчик кнопок модерации отзывов
    application.add_handler(CallbackQueryHandler(review_moderation_callback, pattern="^review_"))

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

    # Редактирование услуг (для специалиста)
    edit_services_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_services_start)],
        states={
            EDIT_SELECT_SERVICE: [CallbackQueryHandler(edit_service_selected, pattern="^edit_")],
            EDIT_SELECT_ACTION: [CallbackQueryHandler(edit_action_selected, pattern="^edit_")],
            EDIT_ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_enter_value)],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel)],
    )
    application.add_handler(edit_services_conv)

    # Блокировка слотов
    block_slot_conv = ConversationHandler(
        entry_points=[CommandHandler("block", block_slot_start)],
        states={
            BLOCK_SELECT_DATE: [CallbackQueryHandler(block_date_selected, pattern="^block_")],
            BLOCK_SELECT_TIME: [CallbackQueryHandler(block_time_selected, pattern="^block_")],
            BLOCK_SELECT_DURATION: [CallbackQueryHandler(block_duration_selected, pattern="^block_")],
        },
        fallbacks=[CommandHandler("cancel", block_cancel)],
    )
    application.add_handler(block_slot_conv)

    # Разблокировка слотов
    unblock_slot_conv = ConversationHandler(
        entry_points=[CommandHandler("unblock", unblock_slot_start)],
        states={
            UNBLOCK_SELECT_DATE: [CallbackQueryHandler(unblock_date_selected, pattern="^unblock_")],
            UNBLOCK_SELECT_SLOT: [CallbackQueryHandler(unblock_slot_selected, pattern="^unblock_")],
        },
        fallbacks=[CommandHandler("cancel", unblock_cancel)],
    )
    application.add_handler(unblock_slot_conv)

    # Управление расписанием салона
    schedule_conv = ConversationHandler(
        entry_points=[CommandHandler("schedule", schedule_manage)],
        states={
            SCHEDULE_SELECT_DAY: [CallbackQueryHandler(schedule_day_selected, pattern="^sched_")],
            SCHEDULE_SELECT_ACTION: [CallbackQueryHandler(schedule_action_selected, pattern="^sched_")],
            SCHEDULE_ENTER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_enter_time)],
        },
        fallbacks=[CommandHandler("cancel", schedule_cancel)],
    )
    application.add_handler(schedule_conv)

    # Персональное расписание мастера
    myschedule_conv = ConversationHandler(
        entry_points=[CommandHandler("myschedule", myschedule_start)],
        states={
            MYSCHEDULE_SELECT_DAY: [CallbackQueryHandler(myschedule_day_selected, pattern="^mysched_")],
            MYSCHEDULE_SELECT_ACTION: [CallbackQueryHandler(myschedule_action_selected, pattern="^mysched_")],
            MYSCHEDULE_ENTER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, myschedule_enter_time)],
        },
        fallbacks=[CommandHandler("cancel", myschedule_cancel)],
    )
    application.add_handler(myschedule_conv)

    # Обработчик для всех остальных сообщений (для неавторизованных)
    application.add_handler(MessageHandler(filters.ALL, unauthorized_handler))

    # Отправляем инструкцию специалисту при запуске
    application.post_init = send_specialist_welcome

    # Запускаем бота
    print("🤖 Telegram бот (приватный) запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
