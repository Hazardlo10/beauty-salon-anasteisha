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
