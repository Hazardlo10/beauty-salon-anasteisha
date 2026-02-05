"""
Главный файл FastAPI приложения
Beauty Salon Booking System - Anasteisha
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
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
from .services.notifications import (
    notify_client_booking_confirmed,
    notify_client_booking_cancelled,
    notify_client_reminder
)

settings = get_settings()


# ==================== PREVIEW MODE ====================
COMING_SOON_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anasteisha - Скоро открытие</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600&family=Montserrat:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            font-family: 'Montserrat', sans-serif;
            color: #fff;
            padding: 20px;
        }
        .container {
            text-align: center;
            max-width: 600px;
        }
        .logo {
            font-family: 'Playfair Display', serif;
            font-size: 3.5rem;
            font-weight: 500;
            color: #c9a86c;
            margin-bottom: 10px;
            letter-spacing: 3px;
        }
        .tagline {
            font-size: 1rem;
            color: rgba(255,255,255,0.6);
            margin-bottom: 50px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        .message {
            font-size: 2rem;
            font-weight: 300;
            margin-bottom: 20px;
            line-height: 1.4;
        }
        .message span {
            color: #c9a86c;
        }
        .subtitle {
            font-size: 1.1rem;
            color: rgba(255,255,255,0.7);
            margin-bottom: 40px;
            line-height: 1.6;
        }
        .contact {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(201, 168, 108, 0.15);
            border: 1px solid rgba(201, 168, 108, 0.3);
            padding: 15px 30px;
            border-radius: 50px;
            color: #c9a86c;
            text-decoration: none;
            transition: all 0.3s;
        }
        .contact:hover {
            background: rgba(201, 168, 108, 0.25);
            transform: translateY(-2px);
        }
        .sparkles {
            position: fixed;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            pointer-events: none;
            overflow: hidden;
        }
        .sparkle {
            position: absolute;
            width: 4px;
            height: 4px;
            background: #c9a86c;
            border-radius: 50%;
            animation: sparkle 3s infinite;
            opacity: 0;
        }
        @keyframes sparkle {
            0%, 100% { opacity: 0; transform: scale(0); }
            50% { opacity: 0.8; transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="sparkles">
        <div class="sparkle" style="left: 10%; top: 20%; animation-delay: 0s;"></div>
        <div class="sparkle" style="left: 80%; top: 30%; animation-delay: 0.5s;"></div>
        <div class="sparkle" style="left: 30%; top: 70%; animation-delay: 1s;"></div>
        <div class="sparkle" style="left: 70%; top: 80%; animation-delay: 1.5s;"></div>
        <div class="sparkle" style="left: 50%; top: 10%; animation-delay: 2s;"></div>
        <div class="sparkle" style="left: 90%; top: 60%; animation-delay: 2.5s;"></div>
    </div>
    <div class="container">
        <div class="logo">Anasteisha</div>
        <div class="tagline">Косметологический кабинет</div>
        <h1 class="message">Сайт <span>скоро</span> откроется</h1>
        <p class="subtitle">Мы готовим для вас удобный сервис онлайн-записи на косметологические процедуры</p>
        <a href="tel:+79991234567" class="contact">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/>
            </svg>
            Позвонить
        </a>
    </div>
</body>
</html>"""


class PreviewModeMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения доступа в режиме превью"""

    async def dispatch(self, request: Request, call_next):
        # Если превью-режим выключен - пропускаем всё
        if not settings.PREVIEW_MODE:
            return await call_next(request)

        path = request.url.path

        # Всегда разрешаем:
        # - API endpoints (для работы форм)
        # - Статические файлы (CSS/JS/изображения)
        # - Webhook endpoints
        allowed_prefixes = ["/api/", "/static/", "/docs", "/redoc", "/openapi"]
        if any(path.startswith(prefix) for prefix in allowed_prefixes):
            return await call_next(request)

        # Проверяем ключ превью
        preview_key = request.query_params.get("preview")

        # Также проверяем cookie (чтобы не передавать ключ на каждой странице)
        if not preview_key:
            preview_key = request.cookies.get("preview_key")

        if preview_key == settings.PREVIEW_KEY:
            # Ключ верный - пропускаем и ставим cookie
            response = await call_next(request)
            # Устанавливаем cookie на 24 часа
            response.set_cookie(
                key="preview_key",
                value=preview_key,
                max_age=86400,
                httponly=True
            )
            return response

        # Ключа нет или неверный - показываем заглушку
        return HTMLResponse(content=COMING_SOON_HTML, status_code=200)


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


class ConsultationRequest(BaseModel):
    service_name: str
    service_id: int = 0
    phone: str


async def send_telegram_to_salon(text: str, reply_markup: dict = None) -> bool:
    """Отправка сообщения СПЕЦИАЛИСТУ (записи, отзывы)"""
    # Сначала пробуем бот специалиста, если не настроен - используем основной
    bot_token = settings.TELEGRAM_SALON_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_SALON_CHAT_ID or settings.TELEGRAM_ADMIN_CHAT_ID

    if not bot_token or not chat_id:
        print("Telegram для специалиста не настроен")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            if response.status_code != 200:
                # Уведомить разработчика об ошибке отправки специалисту
                await send_telegram_to_developer(
                    f"⚠️ <b>Ошибка отправки специалисту</b>\n\n"
                    f"Код: {response.status_code}\n"
                    f"Сообщение не доставлено!"
                )
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки в Telegram (специалист): {e}")
        # Уведомить разработчика
        await send_telegram_to_developer(
            f"🚨 <b>Telegram специалиста недоступен!</b>\n\n"
            f"Ошибка: {str(e)[:200]}"
        )
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


async def notify_dev_error(error_type: str, error_msg: str, context: str = ""):
    """Уведомить разработчика о критической ошибке"""
    message = (
        f"🚨 <b>ОШИБКА СИСТЕМЫ</b>\n\n"
        f"<b>Тип:</b> {error_type}\n"
        f"<b>Ошибка:</b> {error_msg}\n"
    )
    if context:
        message += f"<b>Контекст:</b> {context}\n"
    message += f"\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

    await send_telegram_to_developer(message)


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

# Инициализация услуг по умолчанию
def init_default_services():
    """Добавить услуги в БД если их нет"""
    db = SessionLocal()
    try:
        existing = db.query(Service).count()
        if existing > 0:
            return  # Услуги уже есть

        # Начальные услуги с подробными описаниями
        services_data = [
            {
                "name": "Атравматическая чистка лица",
                "description": "Деликатная процедура глубокого очищения без механического воздействия. Использует энзимные и кислотные пилинги для растворения загрязнений. Идеально подходит для чувствительной, куперозной кожи и при акне. Результат: чистая, сияющая кожа без воспалений.",
                "duration_minutes": 60, "price": 2500, "category": "Лицо", "is_active": True
            },
            {
                "name": "Лифтинг-омоложение лица",
                "description": "Интенсивная антивозрастная процедура с использованием профессиональных пептидных комплексов. Стимулирует выработку коллагена и эластина, подтягивает овал лица, разглаживает морщины. Эффект заметен уже после первого сеанса.",
                "duration_minutes": 90, "price": 2800, "category": "Лицо", "is_active": True
            },
            {
                "name": "Липосомальное обновление кожи",
                "description": "Инновационная процедура доставки активных веществ в глубокие слои кожи с помощью липосом. Обеспечивает интенсивное увлажнение, питание и регенерацию. Кожа становится упругой, бархатистой, цвет лица выравнивается.",
                "duration_minutes": 90, "price": 2800, "category": "Лицо", "is_active": True
            },
            {
                "name": "Ферментотерапия лица",
                "description": "Мягкий энзимный пилинг на основе натуральных ферментов папайи и ананаса. Деликатно растворяет ороговевшие клетки, очищает поры, выравнивает текстуру кожи. Подходит для всех типов кожи, включая чувствительную.",
                "duration_minutes": 75, "price": 2800, "category": "Лицо", "is_active": True
            },
            {
                "name": "Безынъекционный ботокс лица",
                "description": "Процедура с использованием аргирелина и пептидов, имитирующих действие ботулотоксина. Расслабляет мимические мышцы, разглаживает морщины лба и межбровья. Безопасная альтернатива инъекциям с накопительным эффектом.",
                "duration_minutes": 90, "price": 2800, "category": "Лицо", "is_active": True
            },
            {
                "name": "Атравматическая чистка спины",
                "description": "Профессиональное очищение кожи спины от высыпаний, черных точек и воспалений. Включает распаривание, энзимный пилинг, экстракцию, успокаивающую маску. Решает проблемы акне на спине, нормализует работу сальных желез.",
                "duration_minutes": 90, "price": 4500, "category": "Комплекс", "is_active": True
            },
            {
                "name": "Лифтинг шеи и декольте",
                "description": "Специальный уход за деликатной зоной шеи и декольте. Устраняет дряблость, пигментацию, мелкие морщины. Использует коллагеновые маски и моделирующий массаж. Возвращает коже молодость и упругость.",
                "duration_minutes": 75, "price": 3500, "category": "Комплекс", "is_active": True
            },
            {
                "name": "Обновление лица и декольте",
                "description": "Комплексная anti-age программа для лица и зоны декольте. Включает пилинг, сыворотки с гиалуроновой кислотой, коллагеновую маску и массаж. Омолаживает, увлажняет, выравнивает тон кожи.",
                "duration_minutes": 120, "price": 3500, "category": "Комплекс", "is_active": True
            },
            {
                "name": "Ботокс лица и шеи",
                "description": "Расширенная безынъекционная процедура ботокс-эффекта для лица и шеи. Пептидные комплексы расслабляют мимику, лифтинг-маска подтягивает контуры. Результат: разглаживание морщин, четкий овал лица.",
                "duration_minutes": 105, "price": 3800, "category": "Комплекс", "is_active": True
            },
        ]

        for data in services_data:
            service = Service(**data)
            db.add(service)

        db.commit()
        print(f"✅ Добавлено {len(services_data)} услуг в базу данных")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации услуг: {e}")
        db.rollback()
    finally:
        db.close()

init_default_services()

# Обновление описаний для услуг без описаний
def update_service_descriptions():
    """Обновить описания для услуг, у которых они отсутствуют"""
    descriptions = {
        "Атравматическая чистка лица": "Деликатная процедура глубокого очищения без механического воздействия. Использует энзимные и кислотные пилинги для растворения загрязнений. Идеально подходит для чувствительной, куперозной кожи и при акне. Результат: чистая, сияющая кожа без воспалений.",
        "Лифтинг-омоложение лица": "Интенсивная антивозрастная процедура с использованием профессиональных пептидных комплексов. Стимулирует выработку коллагена и эластина, подтягивает овал лица, разглаживает морщины. Эффект заметен уже после первого сеанса.",
        "Липосомальное обновление кожи": "Инновационная процедура доставки активных веществ в глубокие слои кожи с помощью липосом. Обеспечивает интенсивное увлажнение, питание и регенерацию. Кожа становится упругой, бархатистой, цвет лица выравнивается.",
        "Ферментотерапия лица": "Мягкий энзимный пилинг на основе натуральных ферментов папайи и ананаса. Деликатно растворяет ороговевшие клетки, очищает поры, выравнивает текстуру кожи. Подходит для всех типов кожи, включая чувствительную.",
        "Безынъекционный ботокс лица": "Процедура с использованием аргирелина и пептидов, имитирующих действие ботулотоксина. Расслабляет мимические мышцы, разглаживает морщины лба и межбровья. Безопасная альтернатива инъекциям с накопительным эффектом.",
        "Атравматическая чистка спины": "Профессиональное очищение кожи спины от высыпаний, черных точек и воспалений. Включает распаривание, энзимный пилинг, экстракцию, успокаивающую маску. Решает проблемы акне на спине, нормализует работу сальных желез.",
        "Лифтинг шеи и декольте": "Специальный уход за деликатной зоной шеи и декольте. Устраняет дряблость, пигментацию, мелкие морщины. Использует коллагеновые маски и моделирующий массаж. Возвращает коже молодость и упругость.",
        "Обновление лица и декольте": "Комплексная anti-age программа для лица и зоны декольте. Включает пилинг, сыворотки с гиалуроновой кислотой, коллагеновую маску и массаж. Омолаживает, увлажняет, выравнивает тон кожи.",
        "Ботокс лица и шеи": "Расширенная безынъекционная процедура ботокс-эффекта для лица и шеи. Пептидные комплексы расслабляют мимику, лифтинг-маска подтягивает контуры. Результат: разглаживание морщин, четкий овал лица.",
    }

    db = SessionLocal()
    try:
        services = db.query(Service).filter(
            (Service.description == None) | (Service.description == "")
        ).all()

        updated = 0
        for service in services:
            if service.name in descriptions:
                service.description = descriptions[service.name]
                updated += 1

        if updated > 0:
            db.commit()
            print(f"✅ Обновлено описаний для {updated} услуг")
    except Exception as e:
        print(f"⚠️ Ошибка обновления описаний: {e}")
        db.rollback()
    finally:
        db.close()

update_service_descriptions()

# Инициализация отзывов по умолчанию
def init_default_reviews():
    """Добавить начальные отзывы в БД с разными датами"""
    db = SessionLocal()
    try:
        existing = db.query(Review).count()
        if existing > 0:
            return  # Отзывы уже есть

        # Разные даты для отзывов (за последние 3 месяца)
        reviews_data = [
            {
                "name": "Анна М.",
                "rating": 5,
                "text": "Потрясающий результат после чистки лица! Кожа светится изнутри, поры сузились. Анастасия — настоящий профессионал, всё объясняет, подбирает уход индивидуально. Обязательно вернусь!",
                "service": "Атравматическая чистка лица",
                "is_published": True,
                "created_at": datetime.now() - timedelta(days=3)
            },
            {
                "name": "Елена К.",
                "rating": 5,
                "text": "Делала лифтинг-омоложение, эффект превзошёл все ожидания! Овал лица подтянулся, мелкие морщинки разгладились. Очень приятная атмосфера и внимательное отношение.",
                "service": "Лифтинг-омоложение лица",
                "is_published": True,
                "created_at": datetime.now() - timedelta(days=12)
            },
            {
                "name": "Марина В.",
                "rating": 5,
                "text": "Хожу на процедуры регулярно уже полгода. Кожа преобразилась — стала упругой, ровной, сияющей. Рекомендую всем, кто хочет выглядеть моложе без инъекций!",
                "service": "Липосомальное обновление кожи",
                "is_published": True,
                "created_at": datetime.now() - timedelta(days=28)
            },
            {
                "name": "Ольга Д.",
                "rating": 5,
                "text": "Безынъекционный ботокс — это находка! Морщинки на лбу стали менее заметны, лицо выглядит отдохнувшим. И никаких уколов! Спасибо за профессионализм.",
                "service": "Безынъекционный ботокс лица",
                "is_published": True,
                "created_at": datetime.now() - timedelta(days=45)
            },
            {
                "name": "Светлана П.",
                "rating": 5,
                "text": "Замечательный специалист и отличный результат! После комплексной процедуры лица и декольте кожа как шёлк. Буду рекомендовать подругам!",
                "service": "Обновление лица и декольте",
                "is_published": True,
                "created_at": datetime.now() - timedelta(days=67)
            },
        ]

        for data in reviews_data:
            review = Review(**data)
            db.add(review)

        db.commit()
        print(f"✅ Добавлено {len(reviews_data)} отзывов в базу данных")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации отзывов: {e}")
        db.rollback()
    finally:
        db.close()

# Обновление дат существующих отзывов
def update_review_dates():
    """Обновить даты отзывов, чтобы они были разными"""
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.is_published == True).order_by(Review.id).all()
        if not reviews:
            return

        # Разные интервалы для каждого отзыва
        date_offsets = [3, 12, 28, 45, 67]

        for i, review in enumerate(reviews[:5]):
            days_ago = date_offsets[i] if i < len(date_offsets) else (i + 1) * 15
            review.created_at = datetime.now() - timedelta(days=days_ago)

        db.commit()
        print(f"✅ Обновлены даты для {min(len(reviews), 5)} отзывов")
    except Exception as e:
        print(f"⚠️ Ошибка обновления дат отзывов: {e}")
        db.rollback()
    finally:
        db.close()

init_default_reviews()
update_review_dates()

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

# Session Middleware (для админки)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Preview Mode Middleware (ограничение доступа)
app.add_middleware(PreviewModeMiddleware)

# Подключение роутеров
app.include_router(appointments_router)

# Админ-панель (только для разработчика)
try:
    from .admin import setup_admin
    setup_admin(app, engine)
    print("✅ Админ-панель доступна: http://localhost:8000/admin")
except ImportError as e:
    print(f"⚠️ Админ-панель недоступна (установите sqladmin): {e}")

# Статические файлы
frontend_path = Path(__file__).parent.parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# ==================== НАПОМИНАНИЯ КЛИЕНТАМ ====================

async def send_appointment_reminders():
    """Отправить напоминания клиентам о записях на завтра"""
    db = SessionLocal()
    tomorrow = date.today() + timedelta(days=1)
    sent_count = 0

    try:
        # Находим все подтверждённые записи на завтра
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date == tomorrow,
            Appointment.status == "confirmed"
        ).all()

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

        print(f"✅ Отправлено напоминаний: {sent_count}")
        return sent_count

    except Exception as e:
        print(f"❌ Ошибка отправки напоминаний: {e}")
        return 0
    finally:
        db.close()


@app.get("/api/admin/send-reminders")
async def trigger_reminders():
    """Ручной запуск отправки напоминаний (для cron)"""
    count = await send_appointment_reminders()
    return {"success": True, "reminders_sent": count}


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
        await notify_dev_error("БД", str(e), "Не удалось загрузить услуги")
    finally:
        db.close()

    # Fallback - хардкод услуги если БД пустая (с описаниями)
    return [
        {"id": 1, "name": "Атравматическая чистка лица", "price": 2500, "duration_minutes": 60, "category": "Лицо", "description": "Деликатная процедура глубокого очищения без механического воздействия. Идеально для чувствительной кожи.", "image_url": None},
        {"id": 2, "name": "Лифтинг-омоложение лица", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": "Интенсивная антивозрастная процедура. Стимулирует коллаген, подтягивает овал лица.", "image_url": None},
        {"id": 3, "name": "Липосомальное обновление кожи", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": "Инновационная доставка активных веществ в глубокие слои кожи. Увлажнение и регенерация.", "image_url": None},
        {"id": 4, "name": "Ферментотерапия лица", "price": 2800, "duration_minutes": 75, "category": "Лицо", "description": "Мягкий энзимный пилинг на основе натуральных ферментов. Подходит для всех типов кожи.", "image_url": None},
        {"id": 5, "name": "Безынъекционный ботокс лица", "price": 2800, "duration_minutes": 90, "category": "Лицо", "description": "Пептиды расслабляют мимические мышцы, разглаживают морщины. Безопасная альтернатива инъекциям.", "image_url": None},
        {"id": 6, "name": "Атравматическая чистка спины", "price": 4500, "duration_minutes": 90, "category": "Комплекс", "description": "Профессиональное очищение кожи спины от высыпаний и воспалений. Решает проблемы акне.", "image_url": None},
        {"id": 7, "name": "Лифтинг шеи и декольте", "price": 3500, "duration_minutes": 75, "category": "Комплекс", "description": "Уход за деликатной зоной шеи и декольте. Устраняет дряблость и мелкие морщины.", "image_url": None},
        {"id": 8, "name": "Обновление лица и декольте", "price": 3500, "duration_minutes": 120, "category": "Комплекс", "description": "Комплексная anti-age программа. Пилинг, сыворотки, коллагеновая маска и массаж.", "image_url": None},
        {"id": 9, "name": "Ботокс лица и шеи", "price": 3800, "duration_minutes": 105, "category": "Комплекс", "description": "Расширенная безынъекционная процедура ботокс-эффекта. Результат: четкий овал лица.", "image_url": None},
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
        await notify_dev_error("БД", str(e), f"Запись: {booking.name}, {booking.phone}")
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


@app.get("/api/reviews")
async def get_reviews():
    """Получить опубликованные отзывы"""
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.is_published == True
        ).order_by(Review.created_at.desc()).limit(10).all()

        return [
            {
                "id": r.id,
                "name": r.name,
                "rating": r.rating,
                "text": r.text,
                "service": r.service,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ]
    except Exception as e:
        print(f"Ошибка загрузки отзывов: {e}")
        await notify_dev_error("БД", str(e), "Не удалось загрузить отзывы")
        return []
    finally:
        db.close()


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
        await notify_dev_error("БД", str(e), f"Отзыв от: {review.name}")
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

⏳ <b>Ожидает модерации</b>
"""

    # Кнопки модерации
    reply_markup = None
    if review_id:
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Опубликовать", "callback_data": f"review_approve_{review_id}"},
                    {"text": "❌ Отклонить", "callback_data": f"review_reject_{review_id}"}
                ]
            ]
        }

    # Отправляем СПЕЦИАЛИСТУ с кнопками
    sent = await send_telegram_to_salon(message, reply_markup)

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


class SupportRequest(BaseModel):
    name: str = ""
    email: str = ""
    message: str
    page_url: str = ""


@app.post("/api/support")
async def create_support_request(support: SupportRequest):
    """Запрос в техподдержку - отправляется разработчику"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Формируем сообщение для Telegram разработчика
    message = f"""🔧 <b>ПРОБЛЕМА НА САЙТЕ</b> 🔧
══════════════════════════

👤 <b>От кого:</b> {support.name or "Аноним"}
📧 <b>Email:</b> {support.email or "—"}
🔗 <b>Страница:</b> {support.page_url or "—"}

━━━━━━━━━━━━━━━━━━
📋 <b>ОПИСАНИЕ ПРОБЛЕМЫ:</b>
{support.message}
━━━━━━━━━━━━━━━━━━

🕐 {now}
══════════════════════════
"""

    # Отправляем РАЗРАБОТЧИКУ
    sent = await send_telegram_to_developer(message)

    if not sent:
        print("Не удалось отправить сообщение в Telegram")

    return {"success": True, "message": "Сообщение отправлено!"}


@app.post("/api/consultation")
async def create_consultation_request(consultation: ConsultationRequest):
    """Запрос на консультацию по услуге"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Формируем сообщение для специалиста
    message = f"""💬 <b>ЗАПРОС НА КОНСУЛЬТАЦИЮ</b>
━━━━━━━━━━━━━━━━━━

💅 <b>Услуга:</b> {consultation.service_name}
📞 <b>Телефон:</b> {consultation.phone}

🕐 {now}

<i>Клиент интересуется процедурой.
Рекомендуется перезвонить.</i>
"""

    # Отправляем специалисту
    sent = await send_telegram_to_salon(message)

    if not sent:
        raise HTTPException(status_code=500, detail="Не удалось отправить запрос")

    return {"success": True, "message": "Запрос отправлен!"}


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

        # Модерация отзывов: review_approve_123 или review_reject_123
        elif callback_data.startswith("review_approve_"):
            review_id = int(callback_data.replace("review_approve_", ""))
            db = SessionLocal()
            try:
                review = db.query(Review).filter(Review.id == review_id).first()
                if review:
                    review.is_published = True
                    db.commit()

                    await answer_callback_query(callback_id, "✅ Отзыв опубликован!")
                    await edit_message_reply_markup(chat_id, message_id, None)

                    stars = "⭐" * review.rating
                    await send_message_with_keyboard(
                        chat_id,
                        f"✅ <b>ОТЗЫВ #{review_id} ОПУБЛИКОВАН</b>\n\n"
                        f"{stars}\n"
                        f"👤 {review.name}\n"
                        f"<i>\"{review.text[:100]}{'...' if len(review.text) > 100 else ''}\"</i>\n\n"
                        f"Отзыв теперь виден на сайте!",
                        None
                    )
                else:
                    await answer_callback_query(callback_id, "❌ Отзыв не найден")
            finally:
                db.close()

        elif callback_data.startswith("review_reject_"):
            review_id = int(callback_data.replace("review_reject_", ""))
            db = SessionLocal()
            try:
                review = db.query(Review).filter(Review.id == review_id).first()
                if review:
                    review_name = review.name
                    review_text = review.text[:50]
                    db.delete(review)
                    db.commit()

                    await answer_callback_query(callback_id, "❌ Отзыв отклонён и удалён")
                    await edit_message_reply_markup(chat_id, message_id, None)

                    await send_message_with_keyboard(
                        chat_id,
                        f"❌ <b>ОТЗЫВ #{review_id} ОТКЛОНЁН</b>\n\n"
                        f"👤 {review_name}\n"
                        f"<i>\"{review_text}...\"</i>\n\n"
                        f"Отзыв удалён из базы данных.",
                        None
                    )
                else:
                    await answer_callback_query(callback_id, "❌ Отзыв не найден")
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
