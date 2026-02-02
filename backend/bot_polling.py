"""
Telegram Bot Polling для локальной разработки
Запускать отдельно: python bot_polling.py
"""
import asyncio
import httpx
from app.config import get_settings
from app.database import SessionLocal
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.service import Service
from app.services.notifications import notify_client_booking_confirmed, notify_client_booking_cancelled

settings = get_settings()

BOT_TOKEN = settings.TELEGRAM_SALON_BOT_TOKEN
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


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

    finally:
        db.close()


async def main():
    """Основной цикл polling"""
    print(f"[BOT] Запуск polling для бота специалиста...")
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

                        if text == "/start":
                            await send_message(chat_id, "Привет! Я бот для управления записями салона Anasteisha.")
                        elif text == "/help":
                            await send_message(chat_id, "Команды:\n/today - записи на сегодня\n/week - записи на неделю")

        except Exception as e:
            print(f"[BOT] Ошибка: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
