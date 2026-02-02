"""
Скрипт инициализации базы данных
Создаёт таблицы и добавляет начальные данные
"""
import sys
sys.path.insert(0, '.')

from app.database import engine, Base, SessionLocal
from app.models.service import Service
from app.models.client import Client
from app.models.appointment import Appointment
from app.models.booking_lead import BookingLead
from app.models.review import Review
from app.models.problem_report import ProblemReport

# Создаём все таблицы
print("Создание таблиц...")
Base.metadata.create_all(bind=engine)
print("Таблицы созданы!")

# Начальные услуги
INITIAL_SERVICES = [
    {
        "name": "Атравматическая чистка лица",
        "description": "Бережное очищение кожи без механического воздействия. Подходит для чувствительной кожи.",
        "duration_minutes": 60,
        "price": 2500,
        "category": "Лицо",
        "is_active": True
    },
    {
        "name": "Лифтинг-омоложение лица",
        "description": "Процедура для подтяжки и омоложения кожи лица с видимым эффектом.",
        "duration_minutes": 90,
        "price": 2800,
        "category": "Лицо",
        "is_active": True
    },
    {
        "name": "Липосомальное обновление кожи",
        "description": "Глубокое питание и обновление кожи с использованием липосомальных комплексов.",
        "duration_minutes": 90,
        "price": 2800,
        "category": "Лицо",
        "is_active": True
    },
    {
        "name": "Ферментотерапия лица",
        "description": "Обновление кожи с помощью ферментов для мягкого пилинга.",
        "duration_minutes": 75,
        "price": 2800,
        "category": "Лицо",
        "is_active": True
    },
    {
        "name": "Безынъекционный ботокс лица",
        "description": "Расслабление мимических мышц без инъекций для разглаживания морщин.",
        "duration_minutes": 90,
        "price": 2800,
        "category": "Лицо",
        "is_active": True
    },
    {
        "name": "Атравматическая чистка спины",
        "description": "Глубокое очищение кожи спины. Решение проблем с высыпаниями.",
        "duration_minutes": 90,
        "price": 4500,
        "category": "Комплекс",
        "is_active": True
    },
    {
        "name": "Лифтинг шеи и декольте",
        "description": "Подтяжка и омоложение зоны шеи и декольте.",
        "duration_minutes": 75,
        "price": 3500,
        "category": "Комплекс",
        "is_active": True
    },
    {
        "name": "Обновление лица и декольте",
        "description": "Комплексная процедура обновления кожи лица и зоны декольте.",
        "duration_minutes": 120,
        "price": 3500,
        "category": "Комплекс",
        "is_active": True
    },
    {
        "name": "Ботокс лица и шеи",
        "description": "Безынъекционная процедура ботокс-эффекта для лица и шеи.",
        "duration_minutes": 105,
        "price": 3800,
        "category": "Комплекс",
        "is_active": True
    },
]


def init_services():
    """Добавить начальные услуги"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже услуги
        existing = db.query(Service).count()
        if existing > 0:
            print(f"Услуги уже существуют ({existing} шт.), пропускаем...")
            return

        # Добавляем услуги
        for service_data in INITIAL_SERVICES:
            service = Service(**service_data)
            db.add(service)

        db.commit()
        print(f"Добавлено {len(INITIAL_SERVICES)} услуг!")

    finally:
        db.close()


if __name__ == "__main__":
    init_services()
    print("\nИнициализация завершена!")
    print("Теперь можно запустить сервер: python -m uvicorn app.main:app --reload")
