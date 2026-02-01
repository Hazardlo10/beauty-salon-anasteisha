# 🚀 Инструкция по размещению сайта в интернете

Полное руководство по развертыванию системы онлайн-записи Beauty в production.

## 📋 Что нужно для работы сайта в интернете

### 1. Домен (имя сайта)
- **Что**: beauty-salon.ru, my-beauty.ru и т.д.
- **Где купить**: Reg.ru, Timeweb, Nic.ru
- **Цена**: 200-500 ₽/год (.ru домен)

### 2. VPS хостинг (виртуальный сервер)
- **Что**: Сервер для размещения сайта и базы данных
- **Почему VPS**: FastAPI требует ASGI, не работает на обычном хостинге
- **Цена**: от 200-600 ₽/месяц

### 3. SSL сертификат (HTTPS)
- **Что**: Защита данных (обязательно для оплаты)
- **Где**: Let's Encrypt (бесплатно) или у хостера
- **Цена**: 0 ₽ (Let's Encrypt)

---

## 💰 Рекомендуемые VPS провайдеры (Россия, 2026)

### Вариант 1: Timeweb (рекомендую для начинающих)
- **Цена**: от 180 ₽/мес
- **Плюсы**:
  - Простая панель управления
  - 10 дней бесплатно для теста
  - Техподдержка на русском 24/7
  - PostgreSQL легко установить
- **Конфигурация**: 1 vCPU, 1 GB RAM, 10 GB SSD
- **Где**: https://timeweb.com/ru/services/vds/

### Вариант 2: Beget
- **Цена**: от 210 ₽/мес
- **Плюсы**:
  - 99.98% SLA
  - NVMe диски (быстрые)
  - KVM виртуализация
- **Конфигурация**: подходит для небольших проектов

### Вариант 3: FirstVDS
- **Цена**: от 219 ₽/мес
- **Плюсы**:
  - Серверы в России, Нидерландах, Казахстане
  - Хорошая производительность
- **Конфигурация**: базовый тариф

### Вариант 4: RUVDS
- **Цена**: зависит от конфигурации
- **Плюсы**:
  - Надежный провайдер
  - Гибкие настройки
  - DDoS защита

---

## 🛠️ Пошаговая инструкция по размещению

### ШАГ 1: Регистрация домена

1. Выбрать регистратора (Reg.ru, Timeweb, Nic.ru)
2. Проверить доступность домена
3. Зарегистрировать домен (200-500 ₽/год)
4. Пока не трогать DNS настройки

### ШАГ 2: Аренда VPS сервера

**Рекомендую Timeweb для начала:**

1. Зайти на https://timeweb.com/ru/services/vds/
2. Выбрать тариф "VDS-1" (180 ₽/мес):
   - 1 vCPU
   - 1 GB RAM
   - 10 GB SSD NVMe
   - Ubuntu 22.04 LTS
3. Активировать 10 дней бесплатно
4. При заказе выбрать:
   - ОС: Ubuntu 22.04 LTS
   - Локация: Россия
5. Получить данные для доступа:
   - IP адрес сервера
   - Пароль root

### ШАГ 3: Подключение домена к серверу

1. В панели регистратора домена найти "DNS настройки"
2. Создать A-запись:
   ```
   Тип: A
   Имя: @
   Значение: [IP адрес вашего VPS]
   TTL: 3600
   ```
3. Создать A-запись для www:
   ```
   Тип: A
   Имя: www
   Значение: [IP адрес вашего VPS]
   TTL: 3600
   ```
4. Подождать 1-24 часа (пропагация DNS)

### ШАГ 4: Подключение к серверу

**Windows:**
```powershell
# Скачать и установить PuTTY или использовать PowerShell
ssh root@ваш-ip-адрес
# Ввести пароль
```

**После подключения:**
```bash
# Обновить систему
apt update && apt upgrade -y

# Установить необходимое ПО
apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nginx git
```

### ШАГ 5: Настройка PostgreSQL

```bash
# Войти в PostgreSQL
sudo -u postgres psql

# Создать базу данных и пользователя
CREATE DATABASE beauty_db;
CREATE USER beauty_user WITH PASSWORD 'сложный_пароль_123';
ALTER ROLE beauty_user SET client_encoding TO 'utf8';
ALTER ROLE beauty_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE beauty_user SET timezone TO 'Europe/Moscow';
GRANT ALL PRIVILEGES ON DATABASE beauty_db TO beauty_user;
\q

# Применить схему базы данных
sudo -u postgres psql -d beauty_db -f /path/to/schema.sql
```

### ШАГ 6: Загрузка проекта на сервер

```bash
# Создать директорию для проекта
mkdir -p /var/www/beauty
cd /var/www/beauty

# Вариант 1: Через Git (если проект в репозитории)
git clone https://your-repo-url.git .

# Вариант 2: Через SCP с вашего компьютера (Windows PowerShell)
# На вашем компьютере:
scp -r C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty root@ваш-ip:/var/www/

# Создать виртуальное окружение
cd /var/www/beauty
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### ШАГ 7: Настройка переменных окружения

```bash
# Создать .env файл
nano /var/www/beauty/.env
```

Вставить настройки:
```env
DATABASE_URL=postgresql://beauty_user:сложный_пароль_123@localhost:5432/beauty_db
SECRET_KEY=сгенерировать_очень_длинный_случайный_ключ_здесь
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

TELEGRAM_BOT_TOKEN=получить_у_@BotFather
TELEGRAM_ADMIN_CHAT_ID=ваш_telegram_id

SMS_API_KEY=получить_на_sms.ru
YOOKASSA_SHOP_ID=получить_на_yookassa.ru
YOOKASSA_SECRET_KEY=получить_на_yookassa.ru

SITE_URL=https://ваш-домен.ru
ADMIN_EMAIL=admin@ваш-домен.ru
ADMIN_PHONE=+79000000000

DEBUG=False
ENVIRONMENT=production
```

Сохранить: `Ctrl+X`, затем `Y`, затем `Enter`

### ШАГ 8: Создание systemd сервиса (автозапуск)

```bash
# Создать файл сервиса
nano /etc/systemd/system/beauty.service
```

Вставить:
```ini
[Unit]
Description=Beauty Salon Booking System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/beauty/backend
Environment="PATH=/var/www/beauty/venv/bin"
ExecStart=/var/www/beauty/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker app.main:app --workers 2 --bind unix:/var/www/beauty/beauty.sock

[Install]
WantedBy=multi-user.target
```

```bash
# Установить права
chown -R www-data:www-data /var/www/beauty

# Запустить сервис
systemctl start beauty
systemctl enable beauty
systemctl status beauty
```

### ШАГ 9: Настройка Nginx (веб-сервер)

```bash
# Создать конфигурацию Nginx
nano /etc/nginx/sites-available/beauty
```

Вставить:
```nginx
server {
    listen 80;
    server_name ваш-домен.ru www.ваш-домен.ru;

    client_max_body_size 10M;

    # Статические файлы
    location /static {
        alias /var/www/beauty/frontend/static;
        expires 30d;
    }

    # Проксирование к FastAPI
    location / {
        proxy_pass http://unix:/var/www/beauty/beauty.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активировать конфигурацию
ln -s /etc/nginx/sites-available/beauty /etc/nginx/sites-enabled/

# Проверить конфигурацию
nginx -t

# Перезапустить Nginx
systemctl restart nginx
```

### ШАГ 10: Установка SSL сертификата (HTTPS)

```bash
# Установить Certbot
apt install -y certbot python3-certbot-nginx

# Получить SSL сертификат
certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru

# Certbot спросит:
# 1. Email для уведомлений
# 2. Согласие с условиями (A)
# 3. Автоматически настроить HTTPS (2)

# Сертификат установлен! Сайт работает по HTTPS
```

Автопродление сертификата:
```bash
# Проверить автопродление
certbot renew --dry-run
```

### ШАГ 11: Настройка Telegram бота

```bash
# Создать systemd сервис для бота
nano /etc/systemd/system/beauty-bot.service
```

```ini
[Unit]
Description=Beauty Telegram Bot
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/beauty/backend
Environment="PATH=/var/www/beauty/venv/bin"
ExecStart=/var/www/beauty/venv/bin/python app/bot/telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl start beauty-bot
systemctl enable beauty-bot
```

### ШАГ 12: Настройка планировщика напоминаний

```bash
nano /etc/systemd/system/beauty-scheduler.service
```

```ini
[Unit]
Description=Beauty Appointment Scheduler
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/beauty/backend
Environment="PATH=/var/www/beauty/venv/bin"
ExecStart=/var/www/beauty/venv/bin/python app/services/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl start beauty-scheduler
systemctl enable beauty-scheduler
```

---

## ✅ Проверка работы

1. **Открыть браузер**: https://ваш-домен.ru
2. **API документация**: https://ваш-домен.ru/docs
3. **Health check**: https://ваш-домен.ru/health

---

## 🔧 Полезные команды для управления

```bash
# Просмотр логов приложения
journalctl -u beauty -f

# Просмотр логов Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Перезапуск после изменений
systemctl restart beauty
systemctl restart nginx

# Проверка статуса
systemctl status beauty
systemctl status beauty-bot
systemctl status beauty-scheduler

# Обновление кода (если через Git)
cd /var/www/beauty
git pull
systemctl restart beauty
```

---

## 💡 Итоговая стоимость запуска

| Компонент | Цена | Периодичность |
|-----------|------|---------------|
| Домен | 200-500 ₽ | в год |
| VPS хостинг | 180-600 ₽ | в месяц |
| SSL сертификат | 0 ₽ | бесплатно |
| **Итого** | **~200 ₽/мес** | минимум |

**Дополнительные расходы** (опционально):
- ЮKassa: 2.8% от платежа
- SMS.ru: ~1-3 ₽/SMS
- Telegram: бесплатно

---

## 📊 Рекомендуемые конфигурации VPS

### Для старта (до 100 записей/день):
- 1 vCPU, 1 GB RAM, 10 GB SSD
- Цена: 180-250 ₽/мес

### Для роста (до 500 записей/день):
- 2 vCPU, 2 GB RAM, 20 GB SSD
- Цена: 400-600 ₽/мес

### Для активного бизнеса (1000+ записей/день):
- 4 vCPU, 4 GB RAM, 40 GB SSD
- Цена: 800-1200 ₽/мес

---

## 🆘 Помощь и поддержка

Если что-то не получается:

1. **Проверить логи**: `journalctl -u beauty -n 100`
2. **Проверить Nginx**: `nginx -t`
3. **Проверить файрвол**: `ufw status`
4. **Обратиться в поддержку хостера** (Timeweb - отличная поддержка)

---

## 🔐 Безопасность

После установки обязательно:

```bash
# Настроить файрвол
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable

# Отключить вход по паролю root (использовать SSH ключи)
# Настроить fail2ban
apt install fail2ban
systemctl enable fail2ban
```

---

## 📚 Дополнительные ресурсы

- [Timeweb документация](https://timeweb.com/ru/services/vds/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Nginx документация](https://nginx.org/ru/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
