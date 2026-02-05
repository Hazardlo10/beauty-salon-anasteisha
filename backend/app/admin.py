"""
Админ-панель для разработчика
Доступ: http://localhost:8000/admin
Логин: admin / Пароль: из .env (ADMIN_PASSWORD) или по умолчанию beauty2024
"""
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from .config import get_settings
from .models.appointment import Appointment
from .models.client import Client
from .models.service import Service
from .models.review import Review
from .models.booking_lead import BookingLead

settings = get_settings()

# Пароль для админки (можно добавить в .env)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = getattr(settings, 'ADMIN_PASSWORD', 'beauty2024')


class AdminAuth(AuthenticationBackend):
    """Простая авторизация для админки"""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)


# ==================== МОДЕЛИ ДЛЯ АДМИНКИ ====================

class AppointmentAdmin(ModelView, model=Appointment):
    """Записи клиентов"""
    name = "Запись"
    name_plural = "Записи"
    icon = "fa-solid fa-calendar-check"

    column_list = [
        Appointment.id,
        Appointment.appointment_date,
        Appointment.appointment_time,
        Appointment.status,
        Appointment.client_id,
        Appointment.service_id,
        Appointment.created_at
    ]
    column_searchable_list = [Appointment.status]
    column_sortable_list = [Appointment.appointment_date, Appointment.created_at, Appointment.status]
    column_default_sort = [(Appointment.appointment_date, True)]

    column_labels = {
        "id": "ID",
        "appointment_date": "Дата",
        "appointment_time": "Время",
        "status": "Статус",
        "client_id": "Клиент",
        "service_id": "Услуга",
        "duration_minutes": "Длительность",
        "notes": "Заметки",
        "created_at": "Создано"
    }


class ClientAdmin(ModelView, model=Client):
    """Клиенты"""
    name = "Клиент"
    name_plural = "Клиенты"
    icon = "fa-solid fa-users"

    column_list = [
        Client.id,
        Client.name,
        Client.phone,
        Client.email,
        Client.telegram_id,
        Client.created_at
    ]
    column_searchable_list = [Client.name, Client.phone, Client.email]
    column_sortable_list = [Client.name, Client.created_at]

    column_labels = {
        "id": "ID",
        "name": "Имя",
        "phone": "Телефон",
        "email": "Email",
        "telegram_id": "Telegram ID",
        "notes": "Заметки",
        "created_at": "Дата регистрации"
    }


class ServiceAdmin(ModelView, model=Service):
    """Услуги"""
    name = "Услуга"
    name_plural = "Услуги"
    icon = "fa-solid fa-spa"

    column_list = [
        Service.id,
        Service.name,
        Service.category,
        Service.price,
        Service.duration_minutes,
        Service.is_active
    ]
    column_searchable_list = [Service.name, Service.category]
    column_sortable_list = [Service.name, Service.price, Service.category]

    column_labels = {
        "id": "ID",
        "name": "Название",
        "category": "Категория",
        "description": "Описание",
        "price": "Цена (₽)",
        "duration_minutes": "Длительность (мин)",
        "is_active": "Активна"
    }


class ReviewAdmin(ModelView, model=Review):
    """Отзывы"""
    name = "Отзыв"
    name_plural = "Отзывы"
    icon = "fa-solid fa-star"

    column_list = [
        Review.id,
        Review.name,
        Review.rating,
        Review.service,
        Review.is_published,
        Review.created_at
    ]
    column_searchable_list = [Review.name, Review.text]
    column_sortable_list = [Review.rating, Review.is_published, Review.created_at]
    column_default_sort = [(Review.created_at, True)]

    column_labels = {
        "id": "ID",
        "name": "Имя",
        "phone": "Телефон",
        "rating": "Оценка",
        "text": "Текст",
        "service": "Услуга",
        "is_published": "Опубликован",
        "telegram_sent": "Отправлен в TG",
        "created_at": "Дата"
    }


class BookingLeadAdmin(ModelView, model=BookingLead):
    """Заявки на запись"""
    name = "Заявка"
    name_plural = "Заявки"
    icon = "fa-solid fa-clipboard-list"

    column_list = [
        BookingLead.id,
        BookingLead.name,
        BookingLead.phone,
        BookingLead.service,
        BookingLead.status,
        BookingLead.telegram_sent,
        BookingLead.created_at
    ]
    column_searchable_list = [BookingLead.name, BookingLead.phone]
    column_sortable_list = [BookingLead.created_at, BookingLead.status]
    column_default_sort = [(BookingLead.created_at, True)]

    column_labels = {
        "id": "ID",
        "name": "Имя",
        "phone": "Телефон",
        "email": "Email",
        "service": "Услуга",
        "message": "Сообщение",
        "status": "Статус",
        "telegram_sent": "Отправлено в TG",
        "created_at": "Создано"
    }


def setup_admin(app, engine):
    """Настройка админ-панели"""
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Anasteisha Admin",
        base_url="/admin"
    )

    # Регистрация моделей
    admin.add_view(AppointmentAdmin)
    admin.add_view(ClientAdmin)
    admin.add_view(ServiceAdmin)
    admin.add_view(ReviewAdmin)
    admin.add_view(BookingLeadAdmin)

    return admin
