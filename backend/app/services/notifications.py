"""
Сервис для отправки уведомлений
Поддерживает разделение на бизнес и технические уведомления
"""
import logging
import traceback
from typing import Optional, List
from datetime import datetime
from enum import Enum

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.notification import Notification

settings = get_settings()
logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Типы уведомлений"""
    # Бизнес-уведомления (для владельца салона)
    NEW_BOOKING = "new_booking"
    CANCELLED_BOOKING = "cancelled_booking"
    RESCHEDULED_BOOKING = "rescheduled_booking"
    REMINDER_SENT = "reminder_sent"
    PAYMENT_RECEIVED = "payment_received"

    # Технические уведомления (только для разработчика)
    ERROR = "error"
    DATABASE_ERROR = "database_error"
    PAYMENT_ERROR = "payment_error"
    SMS_ERROR = "sms_error"
    SYSTEM_WARNING = "system_warning"
    USER_FEEDBACK = "user_feedback"
    PERFORMANCE_ISSUE = "performance_issue"


class NotificationService:
    """Сервис для отправки уведомлений в Telegram"""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        self.dev_chat_id = settings.TELEGRAM_DEV_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_telegram_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown"
    ) -> bool:
        """
        Отправить сообщение в Telegram

        Args:
            chat_id: ID чата получателя
            text: Текст сообщения
            parse_mode: Режим парсинга (Markdown или HTML)

        Returns:
            bool: True если отправлено успешно
        """
        if not chat_id or not self.bot_token:
            logger.warning("Telegram не настроен, пропускаем отправку")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"Уведомление отправлено в чат {chat_id}")
                    return True
                else:
                    logger.error(f"Ошибка отправки в Telegram: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Исключение при отправке в Telegram: {e}")
            return False

    async def send_business_notification(
        self,
        notification_type: NotificationType,
        message: str,
        db: Optional[Session] = None,
        appointment_id: Optional[int] = None
    ):
        """
        Отправить бизнес-уведомление
        Отправляется владельцу салона и разработчику

        Args:
            notification_type: Тип уведомления
            message: Текст сообщения
            db: Сессия БД для логирования
            appointment_id: ID записи (если применимо)
        """
        # Иконки для разных типов уведомлений
        icons = {
            NotificationType.NEW_BOOKING: "🔔",
            NotificationType.CANCELLED_BOOKING: "❌",
            NotificationType.RESCHEDULED_BOOKING: "🔄",
            NotificationType.REMINDER_SENT: "⏰",
            NotificationType.PAYMENT_RECEIVED: "💰",
        }

        icon = icons.get(notification_type, "📢")
        full_message = f"{icon} *{notification_type.value.upper()}*\n\n{message}"

        # Отправляем владельцу салона
        if self.admin_chat_id:
            await self.send_telegram_message(self.admin_chat_id, full_message)

        # Отправляем разработчику (если настроен)
        if self.dev_chat_id:
            dev_message = f"{full_message}\n\n_Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
            await self.send_telegram_message(self.dev_chat_id, dev_message)

        # Логируем в БД
        if db and appointment_id:
            notification = Notification(
                appointment_id=appointment_id,
                notification_type="telegram",
                message=message,
                status="sent"
            )
            db.add(notification)
            db.commit()

    async def send_technical_notification(
        self,
        notification_type: NotificationType,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[dict] = None
    ):
        """
        Отправить техническое уведомление
        Отправляется ТОЛЬКО разработчику

        Args:
            notification_type: Тип уведомления
            message: Текст сообщения
            error: Объект исключения (если есть)
            context: Дополнительный контекст (словарь)
        """
        if not self.dev_chat_id:
            logger.warning("Dev chat ID не настроен, пропускаем техническое уведомление")
            return

        # Иконки для технических уведомлений
        icons = {
            NotificationType.ERROR: "🚨",
            NotificationType.DATABASE_ERROR: "💥",
            NotificationType.PAYMENT_ERROR: "💳",
            NotificationType.SMS_ERROR: "📱",
            NotificationType.SYSTEM_WARNING: "⚠️",
            NotificationType.USER_FEEDBACK: "💬",
            NotificationType.PERFORMANCE_ISSUE: "🐌",
        }

        icon = icons.get(notification_type, "🔧")

        # Формируем сообщение
        full_message = f"{icon} *ТЕХНИЧЕСКОЕ УВЕДОМЛЕНИЕ*\n\n"
        full_message += f"*Тип:* {notification_type.value}\n"
        full_message += f"*Сообщение:* {message}\n"
        full_message += f"*Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        # Добавляем информацию об ошибке
        if error:
            full_message += f"\n*Ошибка:*\n```\n{str(error)}\n```\n"

            # Добавляем traceback
            tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            if len(tb) < 3000:  # Telegram лимит ~4096 символов
                full_message += f"\n*Traceback:*\n```\n{tb}\n```"

        # Добавляем контекст
        if context:
            full_message += f"\n*Контекст:*\n"
            for key, value in context.items():
                full_message += f"• {key}: {value}\n"

        # Отправляем разработчику
        await self.send_telegram_message(self.dev_chat_id, full_message)

        # Логируем в системный лог
        logger.error(f"Technical notification: {notification_type.value} - {message}")
        if error:
            logger.error(f"Error details: {error}")


# Глобальный экземпляр сервиса
notification_service = NotificationService()


# Удобные функции для использования в коде

async def notify_new_booking(
    client_name: str,
    phone: str,
    service: str,
    date: str,
    time: str,
    price: float,
    db: Optional[Session] = None,
    appointment_id: Optional[int] = None
):
    """Уведомление о новой записи"""
    message = (
        f"👤 Клиент: {client_name}\n"
        f"📱 Телефон: {phone}\n\n"
        f"💅 Услуга: {service}\n"
        f"💰 Стоимость: {price} ₽\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}"
    )

    await notification_service.send_business_notification(
        NotificationType.NEW_BOOKING,
        message,
        db,
        appointment_id
    )


async def notify_cancelled_booking(
    client_name: str,
    service: str,
    date: str,
    time: str,
    reason: Optional[str] = None,
    db: Optional[Session] = None,
    appointment_id: Optional[int] = None
):
    """Уведомление об отмене записи"""
    message = (
        f"👤 Клиент: {client_name}\n"
        f"💅 Услуга: {service}\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}\n"
    )

    if reason:
        message += f"\n📝 Причина: {reason}"

    await notification_service.send_business_notification(
        NotificationType.CANCELLED_BOOKING,
        message,
        db,
        appointment_id
    )


async def notify_rescheduled_booking(
    client_name: str,
    service: str,
    old_date: str,
    old_time: str,
    new_date: str,
    new_time: str,
    db: Optional[Session] = None,
    appointment_id: Optional[int] = None
):
    """Уведомление о переносе записи"""
    message = (
        f"👤 Клиент: {client_name}\n"
        f"💅 Услуга: {service}\n\n"
        f"📅 Было: {old_date} в {old_time}\n"
        f"📅 Стало: {new_date} в {new_time}"
    )

    await notification_service.send_business_notification(
        NotificationType.RESCHEDULED_BOOKING,
        message,
        db,
        appointment_id
    )


async def notify_payment_received(
    client_name: str,
    amount: float,
    payment_method: str,
    service: str,
    db: Optional[Session] = None,
    appointment_id: Optional[int] = None
):
    """Уведомление о получении оплаты"""
    message = (
        f"👤 Клиент: {client_name}\n"
        f"💅 Услуга: {service}\n"
        f"💰 Сумма: {amount} ₽\n"
        f"💳 Способ: {payment_method}"
    )

    await notification_service.send_business_notification(
        NotificationType.PAYMENT_RECEIVED,
        message,
        db,
        appointment_id
    )


async def notify_error(
    message: str,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
):
    """Уведомление об ошибке (только разработчику)"""
    await notification_service.send_technical_notification(
        NotificationType.ERROR,
        message,
        error,
        context
    )


async def notify_database_error(
    operation: str,
    error: Exception,
    context: Optional[dict] = None
):
    """Уведомление об ошибке БД (только разработчику)"""
    message = f"Ошибка при операции с БД: {operation}"

    await notification_service.send_technical_notification(
        NotificationType.DATABASE_ERROR,
        message,
        error,
        context
    )


async def notify_payment_error(
    message: str,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
):
    """Уведомление об ошибке оплаты (только разработчику)"""
    await notification_service.send_technical_notification(
        NotificationType.PAYMENT_ERROR,
        message,
        error,
        context
    )


async def notify_user_feedback(
    client_name: str,
    rating: int,
    comment: str,
    service: str
):
    """Уведомление об отзыве пользователя"""
    stars = "⭐" * rating
    message = (
        f"👤 Клиент: {client_name}\n"
        f"💅 Услуга: {service}\n"
        f"⭐ Оценка: {stars} ({rating}/5)\n"
        f"💬 Отзыв: {comment}"
    )

    await notification_service.send_technical_notification(
        NotificationType.USER_FEEDBACK,
        message
    )


async def notify_system_warning(
    message: str,
    context: Optional[dict] = None
):
    """Уведомление о системном предупреждении (только разработчику)"""
    await notification_service.send_technical_notification(
        NotificationType.SYSTEM_WARNING,
        message,
        context=context
    )


# ==================== УВЕДОМЛЕНИЯ КЛИЕНТАМ ====================

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ClientNotificationService:
    """Сервис уведомлений клиентам (Email + Telegram)"""

    @staticmethod
    def _format_date(date_obj) -> str:
        """Форматирование даты на русском"""
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        return f"{date_obj.day} {months[date_obj.month - 1]} ({days[date_obj.weekday()]})"

    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Отправка email клиенту"""
        if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
            logger.warning("Email не настроен (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
            msg['To'] = to_email

            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ClientNotificationService._send_smtp(msg, to_email))
            logger.info(f"Email отправлен: {to_email}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False

    @staticmethod
    def _send_smtp(msg, to_email):
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL or settings.SMTP_USER, to_email, msg.as_string())

    @staticmethod
    async def send_telegram_to_client(telegram_id: int, text: str) -> bool:
        """Отправка Telegram клиенту"""
        bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"chat_id": telegram_id, "text": text, "parse_mode": "HTML"})
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram клиенту: {e}")
            return False

    @staticmethod
    async def send_telegram_to_specialist(text: str) -> bool:
        """Отправка Telegram специалисту"""
        bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_SALON_CHAT_ID or settings.TELEGRAM_ADMIN_CHAT_ID
        if not bot_token or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
                return response.status_code == 200
        except Exception:
            return False

    # ==================== EMAIL ШАБЛОНЫ ====================

    @staticmethod
    def get_booking_created_email(client_name, service_name, appointment_date, appointment_time, price, appointment_id):
        date_str = ClientNotificationService._format_date(appointment_date)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:0 auto;padding:20px}}.header{{background:linear-gradient(135deg,#c9a86c,#b8956a);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0}}.content{{background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px}}.info-box{{background:white;padding:20px;border-radius:8px;margin:20px 0;border-left:4px solid #c9a86c}}.footer{{text-align:center;padding:20px;color:#888;font-size:12px}}.btn{{display:inline-block;background:#c9a86c;color:white;padding:12px 30px;text-decoration:none;border-radius:25px}}</style></head>
<body><div class="container"><div class="header"><h1>Anasteisha</h1><p>Кабинет косметологии</p></div>
<div class="content"><h2>Здравствуйте, {client_name}!</h2><p>Ваша запись создана и ожидает подтверждения.</p>
<div class="info-box"><p><strong>Услуга:</strong> {service_name}</p><p><strong>Дата:</strong> {date_str}</p><p><strong>Время:</strong> {appointment_time}</p><p><strong>Стоимость:</strong> {price:,.0f} ₽</p><p><strong>№ записи:</strong> #{appointment_id}</p></div>
<p>Мы свяжемся с вами для подтверждения.</p><center><a href="{settings.SITE_URL}/my-bookings.html" class="btn">Мои записи</a></center></div>
<div class="footer"><p>г. Анжеро-Судженск, ул. М.Горького 11А</p></div></div></body></html>"""
        text = f"Здравствуйте, {client_name}!\n\nЗапись создана.\nУслуга: {service_name}\nДата: {date_str}\nВремя: {appointment_time}\nСтоимость: {price:,.0f} ₽\n№ записи: #{appointment_id}\n\nМы свяжемся с вами.\n\nAnasteisha"
        return html, text

    @staticmethod
    def get_booking_confirmed_email(client_name, service_name, appointment_date, appointment_time, appointment_id):
        date_str = ClientNotificationService._format_date(appointment_date)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:0 auto;padding:20px}}.header{{background:linear-gradient(135deg,#28a745,#20c997);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0}}.content{{background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px}}.info-box{{background:white;padding:20px;border-radius:8px;margin:20px 0;border-left:4px solid #28a745}}.footer{{text-align:center;padding:20px;color:#888;font-size:12px}}</style></head>
<body><div class="container"><div class="header"><h1>✅ Запись подтверждена!</h1></div>
<div class="content"><h2>Здравствуйте, {client_name}!</h2><p>Ваша запись подтверждена. Ждём вас!</p>
<div class="info-box"><p><strong>Услуга:</strong> {service_name}</p><p><strong>Дата:</strong> {date_str}</p><p><strong>Время:</strong> {appointment_time}</p></div>
<p><strong>Адрес:</strong> г. Анжеро-Судженск, ул. М.Горького 11А</p></div>
<div class="footer"><p>Anasteisha</p></div></div></body></html>"""
        text = f"Здравствуйте, {client_name}!\n\n✅ Запись подтверждена!\n\nУслуга: {service_name}\nДата: {date_str}\nВремя: {appointment_time}\n\nАдрес: г. Анжеро-Судженск, ул. М.Горького 11А\n\nЖдём вас!\nAnasteisha"
        return html, text

    @staticmethod
    def get_booking_cancelled_email(client_name, service_name, appointment_date, appointment_time):
        date_str = ClientNotificationService._format_date(appointment_date)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:0 auto;padding:20px}}.header{{background:#dc3545;color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0}}.content{{background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px}}.btn{{display:inline-block;background:#c9a86c;color:white;padding:12px 30px;text-decoration:none;border-radius:25px}}.footer{{text-align:center;padding:20px;color:#888;font-size:12px}}</style></head>
<body><div class="container"><div class="header"><h1>Запись отменена</h1></div>
<div class="content"><h2>Здравствуйте, {client_name}!</h2><p>Ваша запись была отменена.</p><p><strong>Услуга:</strong> {service_name}</p><p><strong>Дата:</strong> {date_str} в {appointment_time}</p>
<center><a href="{settings.SITE_URL}/#booking" class="btn">Записаться снова</a></center></div>
<div class="footer"><p>Anasteisha</p></div></div></body></html>"""
        text = f"Здравствуйте, {client_name}!\n\nЗапись отменена.\nУслуга: {service_name}\nДата: {date_str} в {appointment_time}\n\nAnasteisha"
        return html, text

    # ==================== TELEGRAM ШАБЛОНЫ ====================

    @staticmethod
    def get_booking_created_tg(client_name, service_name, appointment_date, appointment_time, price, appointment_id):
        date_str = ClientNotificationService._format_date(appointment_date)
        return f"📅 <b>Запись создана!</b>\n\n{client_name}, ваша запись оформлена.\n\n💆 {service_name}\n📆 {date_str}\n🕐 {appointment_time}\n💰 {price:,.0f} ₽\n\n№ #{appointment_id}\n\nМы свяжемся для подтверждения."

    @staticmethod
    def get_booking_confirmed_tg(client_name, service_name, appointment_date, appointment_time):
        date_str = ClientNotificationService._format_date(appointment_date)
        return f"✅ <b>Запись подтверждена!</b>\n\n{client_name}, ждём вас!\n\n💆 {service_name}\n📆 {date_str}\n🕐 {appointment_time}\n\n📍 г. Анжеро-Судженск, ул. М.Горького 11А"

    @staticmethod
    def get_booking_cancelled_tg(client_name, service_name, appointment_date, appointment_time):
        date_str = ClientNotificationService._format_date(appointment_date)
        return f"❌ <b>Запись отменена</b>\n\n{client_name}, ваша запись отменена.\n\n💆 {service_name}\n📆 {date_str} в {appointment_time}"

    # ==================== НАПОМИНАНИЕ СПЕЦИАЛИСТУ ====================

    @staticmethod
    def get_call_reminder(client_name, client_phone, service_name, appointment_date, appointment_time, reason):
        date_str = ClientNotificationService._format_date(appointment_date)
        return f"""📞 <b>ПОЗВОНИТЕ КЛИЕНТУ!</b>

{reason}

👤 <b>Клиент:</b> {client_name}
📞 <b>Телефон:</b> {client_phone}

💆 {service_name}
📆 {date_str}
🕐 {appointment_time}

<i>У клиента нет email/Telegram</i>"""


# ==================== КОМПЛЕКСНЫЕ МЕТОДЫ ====================

async def notify_client_booking_created(
    client_email: Optional[str],
    client_telegram_id: Optional[int],
    client_name: str,
    client_phone: str,
    service_name: str,
    appointment_date,
    appointment_time: str,
    price: float,
    appointment_id: int
):
    """Уведомить клиента о создании записи"""
    sent = False
    tasks = []

    if client_email:
        html, text = ClientNotificationService.get_booking_created_email(
            client_name, service_name, appointment_date, appointment_time, price, appointment_id
        )
        tasks.append(ClientNotificationService.send_email(client_email, f"Запись #{appointment_id} - Anasteisha", html, text))
        sent = True

    if client_telegram_id:
        msg = ClientNotificationService.get_booking_created_tg(
            client_name, service_name, appointment_date, appointment_time, price, appointment_id
        )
        tasks.append(ClientNotificationService.send_telegram_to_client(client_telegram_id, msg))
        sent = True

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Нет контактов → напомнить специалисту позвонить
    if not sent:
        msg = ClientNotificationService.get_call_reminder(
            client_name, client_phone, service_name, appointment_date, appointment_time,
            "Новая запись - позвоните для подтверждения!"
        )
        await ClientNotificationService.send_telegram_to_specialist(msg)


async def notify_client_booking_confirmed(
    client_email: Optional[str],
    client_telegram_id: Optional[int],
    client_name: str,
    client_phone: str,
    service_name: str,
    appointment_date,
    appointment_time: str,
    appointment_id: int
):
    """Уведомить клиента о подтверждении"""
    sent = False
    tasks = []

    if client_email:
        html, text = ClientNotificationService.get_booking_confirmed_email(
            client_name, service_name, appointment_date, appointment_time, appointment_id
        )
        tasks.append(ClientNotificationService.send_email(client_email, "✅ Запись подтверждена - Anasteisha", html, text))
        sent = True

    if client_telegram_id:
        msg = ClientNotificationService.get_booking_confirmed_tg(client_name, service_name, appointment_date, appointment_time)
        tasks.append(ClientNotificationService.send_telegram_to_client(client_telegram_id, msg))
        sent = True

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    if not sent:
        msg = ClientNotificationService.get_call_reminder(
            client_name, client_phone, service_name, appointment_date, appointment_time,
            "Запись подтверждена - сообщите клиенту!"
        )
        await ClientNotificationService.send_telegram_to_specialist(msg)


async def notify_client_booking_cancelled(
    client_email: Optional[str],
    client_telegram_id: Optional[int],
    client_name: str,
    client_phone: str,
    service_name: str,
    appointment_date,
    appointment_time: str
):
    """Уведомить клиента об отмене"""
    sent = False
    tasks = []

    if client_email:
        html, text = ClientNotificationService.get_booking_cancelled_email(client_name, service_name, appointment_date, appointment_time)
        tasks.append(ClientNotificationService.send_email(client_email, "Запись отменена - Anasteisha", html, text))
        sent = True

    if client_telegram_id:
        msg = ClientNotificationService.get_booking_cancelled_tg(client_name, service_name, appointment_date, appointment_time)
        tasks.append(ClientNotificationService.send_telegram_to_client(client_telegram_id, msg))
        sent = True

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    if not sent:
        msg = ClientNotificationService.get_call_reminder(
            client_name, client_phone, service_name, appointment_date, appointment_time,
            "Запись отменена - сообщите клиенту!"
        )
        await ClientNotificationService.send_telegram_to_specialist(msg)


async def notify_client_booking_rescheduled(
    client_email: Optional[str],
    client_telegram_id: Optional[int],
    client_name: str,
    client_phone: str,
    service_name: str,
    old_date,
    old_time: str,
    new_date,
    new_time: str,
    appointment_id: int
):
    """Уведомить клиента о переносе записи"""
    sent = False
    tasks = []

    old_date_str = ClientNotificationService._format_date(old_date)
    new_date_str = ClientNotificationService._format_date(new_date)

    if client_email:
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:0 auto;padding:20px}}.header{{background:linear-gradient(135deg,#17a2b8,#138496);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0}}.content{{background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px}}.info-box{{background:white;padding:20px;border-radius:8px;margin:20px 0;border-left:4px solid #17a2b8}}.old{{text-decoration:line-through;color:#888}}.new{{color:#28a745;font-weight:bold}}.footer{{text-align:center;padding:20px;color:#888;font-size:12px}}</style></head>
<body><div class="container"><div class="header"><h1>🔄 Запись перенесена</h1></div>
<div class="content"><h2>Здравствуйте, {client_name}!</h2><p>Ваша запись была перенесена на новое время.</p>
<div class="info-box"><p><strong>Услуга:</strong> {service_name}</p><p class="old">Было: {old_date_str} в {old_time}</p><p class="new">Новое время: {new_date_str} в {new_time}</p></div>
<p><strong>Адрес:</strong> г. Анжеро-Судженск, ул. М.Горького 11А</p></div>
<div class="footer"><p>Anasteisha</p></div></div></body></html>"""
        text = f"Здравствуйте, {client_name}!\n\n🔄 Запись перенесена\n\nУслуга: {service_name}\nБыло: {old_date_str} в {old_time}\nНовое время: {new_date_str} в {new_time}\n\nАдрес: г. Анжеро-Судженск, ул. М.Горького 11А\n\nAnasteisha"
        tasks.append(ClientNotificationService.send_email(client_email, "🔄 Запись перенесена - Anasteisha", html, text))
        sent = True

    if client_telegram_id:
        msg = f"""🔄 <b>Запись перенесена</b>

{client_name}, ваша запись перенесена на новое время.

💆 {service_name}
❌ <s>Было: {old_date_str} в {old_time}</s>
✅ <b>Новое время: {new_date_str} в {new_time}</b>

📍 г. Анжеро-Судженск, ул. М.Горького 11А"""
        tasks.append(ClientNotificationService.send_telegram_to_client(client_telegram_id, msg))
        sent = True

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    if not sent:
        msg = f"""📞 <b>ПОЗВОНИТЕ КЛИЕНТУ!</b>

Запись перенесена - сообщите клиенту!

👤 <b>Клиент:</b> {client_name}
📞 <b>Телефон:</b> {client_phone}

💆 {service_name}
❌ Было: {old_date_str} в {old_time}
✅ Новое время: {new_date_str} в {new_time}

<i>У клиента нет email/Telegram</i>"""
        await ClientNotificationService.send_telegram_to_specialist(msg)


async def notify_client_reminder(
    client_email: Optional[str],
    client_telegram_id: Optional[int],
    client_name: str,
    client_phone: str,
    service_name: str,
    appointment_date,
    appointment_time: str,
    appointment_id: int
):
    """Напоминание клиенту о записи (за день до визита)"""
    sent = False
    tasks = []

    date_str = ClientNotificationService._format_date(appointment_date)

    if client_email:
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:0 auto;padding:20px}}.header{{background:linear-gradient(135deg,#c9a86c,#b8956a);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0}}.content{{background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px}}.info-box{{background:white;padding:20px;border-radius:8px;margin:20px 0;border-left:4px solid #c9a86c}}.footer{{text-align:center;padding:20px;color:#888;font-size:12px}}</style></head>
<body><div class="container"><div class="header"><h1>⏰ Напоминание о записи</h1></div>
<div class="content"><h2>Здравствуйте, {client_name}!</h2><p>Напоминаем о вашей записи <b>завтра</b>!</p>
<div class="info-box"><p><strong>Услуга:</strong> {service_name}</p><p><strong>Дата:</strong> {date_str}</p><p><strong>Время:</strong> {appointment_time}</p></div>
<p><strong>Адрес:</strong> г. Анжеро-Судженск, ул. М.Горького 11А</p><p>Ждём вас!</p></div>
<div class="footer"><p>Anasteisha</p></div></div></body></html>"""
        text = f"Здравствуйте, {client_name}!\n\n⏰ Напоминание о записи завтра!\n\nУслуга: {service_name}\nДата: {date_str}\nВремя: {appointment_time}\n\nАдрес: г. Анжеро-Судженск, ул. М.Горького 11А\n\nЖдём вас!\nAnasteisha"
        tasks.append(ClientNotificationService.send_email(client_email, "⏰ Напоминание о записи завтра - Anasteisha", html, text))
        sent = True

    if client_telegram_id:
        msg = f"""⏰ <b>Напоминание о записи!</b>

{client_name}, завтра у вас запись!

💆 {service_name}
📆 {date_str}
🕐 {appointment_time}

📍 г. Анжеро-Судженск, ул. М.Горького 11А

Ждём вас! 💖"""
        tasks.append(ClientNotificationService.send_telegram_to_client(client_telegram_id, msg))
        sent = True

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Если нет контактов - напоминаем специалисту позвонить
    if not sent:
        msg = f"""📞 <b>НАПОМНИТЕ КЛИЕНТУ!</b>

Запись завтра - позвоните для напоминания!

👤 <b>Клиент:</b> {client_name}
📞 <b>Телефон:</b> {client_phone}

💆 {service_name}
📆 {date_str}
🕐 {appointment_time}

<i>У клиента нет email/Telegram</i>"""
        await ClientNotificationService.send_telegram_to_specialist(msg)
