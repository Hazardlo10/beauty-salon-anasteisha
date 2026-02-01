# Beauty - Система онлайн-записи для косметологического кабинета

Полнофункциональная система управления записями клиентов с интеграцией Telegram, SMS, онлайн-оплатой.

## Возможности

### Для клиентов:
- Онлайн-запись на услуги через сайт
- Выбор свободного времени в реальном времени
- Уведомления в Telegram и SMS
- Онлайн-оплата услуг
- Личный кабинет с историей посещений
- Система промокодов и скидок

### Для администратора:
- Админ-панель для управления записями
- База клиентов с полной историей
- Управление услугами и ценами
- Настройка расписания работы
- Статистика и аналитика
- Автоматические напоминания клиентам
- Финансовые отчеты

## Технологический стек

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL 14+
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Интеграции**:
  - Telegram Bot API
  - ЮKassa (оплата)
  - SMS.ru (SMS уведомления)

## Установка и запуск

### 1. Требования

- Python 3.11+
- PostgreSQL 14+
- Telegram Bot Token
- Аккаунты: ЮKassa, SMS.ru (опционально)

### 2. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Активировать (Linux/Mac)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 3. Настройка базы данных

```bash
# Создать базу данных PostgreSQL
createdb beauty_db

# Применить схему
psql -U username -d beauty_db -f database/schema.sql
```

### 4. Конфигурация

Создать файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполнить настройки в `.env`:
- DATABASE_URL - строка подключения к PostgreSQL
- TELEGRAM_BOT_TOKEN - токен бота
- SMS_API_KEY - ключ API для SMS
- YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY - данные ЮKassa

### 5. Запуск

```bash
# Запустить Backend (FastAPI)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Запустить Telegram бота (в отдельном терминале)
python backend/app/bot/telegram_bot.py

# Запустить планировщик напоминаний (в отдельном терминале)
python backend/app/services/scheduler.py
```

### 6. Доступ

- **Сайт**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **Админ-панель**: http://localhost:8000/admin

## Структура проекта

```
beauty/
├── backend/
│   └── app/
│       ├── models/          # SQLAlchemy модели
│       ├── routes/          # API endpoints
│       ├── bot/             # Telegram бот
│       ├── services/        # Бизнес-логика
│       ├── config.py        # Конфигурация
│       └── main.py          # Точка входа FastAPI
├── frontend/
│   ├── static/
│   │   ├── css/            # Стили
│   │   ├── js/             # JavaScript
│   │   └── images/         # Изображения
│   └── templates/          # HTML шаблоны
├── database/
│   └── schema.sql          # Схема БД
├── tests/                  # Тесты
├── .env.example           # Пример конфигурации
├── requirements.txt       # Python зависимости
└── README.md
```

## API Endpoints

### Клиенты
- `GET /api/clients` - Список клиентов
- `POST /api/clients` - Создать клиента
- `GET /api/clients/{id}` - Получить клиента
- `PUT /api/clients/{id}` - Обновить клиента

### Услуги
- `GET /api/services` - Список услуг
- `GET /api/services/{id}` - Получить услугу

### Записи
- `GET /api/appointments` - Список записей
- `POST /api/appointments` - Создать запись
- `GET /api/appointments/available-slots` - Доступные слоты
- `PATCH /api/appointments/{id}/status` - Изменить статус

### Оплата
- `POST /api/payments/create` - Создать платеж
- `POST /api/payments/webhook` - Webhook от ЮKassa

## Разработка

### Миграции базы данных

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head
```

### Тесты

```bash
pytest tests/
```

### Форматирование кода

```bash
black backend/
flake8 backend/
```

## Лицензия

MIT

## Автор

Разработано с помощью Claude Code
