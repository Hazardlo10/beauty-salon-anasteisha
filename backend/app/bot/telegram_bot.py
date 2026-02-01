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

# Состояния разговора
SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, ENTERING_PHONE, ENTERING_NAME, CONFIRMING = range(6)


def get_db() -> Session:
    """Получить сессию базы данных"""
    return SessionLocal()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    user = update.effective_user
    telegram_id = user.id

    # Проверяем, есть ли клиент в базе
    db = get_db()
    try:
        client = db.query(Client).filter(Client.telegram_id == telegram_id).first()

        if client:
            welcome_text = f"С возвращением, {client.name}! 🌸\n\n"
        else:
            welcome_text = f"Здравствуйте! 🌸\n\n"

        welcome_text += (
            "Я бот для онлайн-записи в косметологический кабинет Beauty.\n\n"
            "Доступные команды:\n"
            "/book - 📅 Записаться на прием\n"
            "/myappointments - 📋 Мои записи\n"
            "/services - 💅 Список услуг\n"
            "/cancel - ❌ Отменить запись\n"
            "/help - ❓ Помощь\n"
        )

        await update.message.reply_text(welcome_text)
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

    # Запускаем бота
    print("🤖 Telegram бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
