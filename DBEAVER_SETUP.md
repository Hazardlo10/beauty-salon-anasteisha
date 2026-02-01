# 🗄️ Настройка PostgreSQL через DBeaver

**Дата:** 01.02.2026
**Проект:** Anasteisha Beauty Salon

---

## 📋 Чеклист: Что нужно сделать в DBeaver

### ✅ Шаг 1: Создать подключение к PostgreSQL

1. Открыть DBeaver
2. `Database` → `New Database Connection` (или Ctrl+Shift+N)
3. Выбрать **PostgreSQL**
4. Нажать **Next**

### ✅ Шаг 2: Настроить параметры подключения

```
Host: localhost
Port: 5432
Database: postgres
Username: postgres
Password: [ваш пароль от PostgreSQL]
```

Нажать **Test Connection**

**Если ошибка:**
- "Connection refused" → PostgreSQL не запущен (см. ниже как запустить)
- "Authentication failed" → неправильный пароль
- "Driver not found" → нажать Download

### ✅ Шаг 3: Запустить PostgreSQL (если не запущен)

**Способ 1: Через Services**
```
Win+R → services.msc → Enter
Найти: postgresql-x64-XX (где XX - версия)
Правой кнопкой → Start
```

**Способ 2: Через PowerShell (от администратора)**
```powershell
# Проверить статус
Get-Service -Name postgresql*

# Запустить (замените имя на правильное)
Start-Service -Name "postgresql-x64-15"
```

**Способ 3: В DBeaver**
После настройки подключения:
- Правой кнопкой на подключении
- Если доступно: **Start Local Server**

### ✅ Шаг 4: Создать базу данных beauty_db

**Способ 1: Через GUI**
1. Развернуть подключение PostgreSQL в Database Navigator
2. Правой кнопкой на **Databases** → **Create New Database**
3. Ввести:
   ```
   Database name: beauty_db
   Owner: postgres
   Encoding: UTF8
   ```
4. Нажать **OK**

**Способ 2: Через SQL**
1. `SQL Editor` → `New SQL Script` (или F3)
2. Выполнить:
   ```sql
   CREATE DATABASE beauty_db
       WITH OWNER = postgres
       ENCODING = 'UTF8'
       CONNECTION LIMIT = -1;
   ```
3. Нажать `Ctrl+Enter` или ▶️

### ✅ Шаг 5: Применить схему базы данных

1. **Подключиться к beauty_db:**
   - В Database Navigator развернуть **Databases**
   - Найти **beauty_db**
   - Двойной клик

2. **Открыть schema.sql:**
   - `File` → `Open File` (или Ctrl+O)
   - Выбрать: `C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty\database\schema.sql`

3. **Выполнить скрипт:**
   - Убедиться что выбрана база **beauty_db** (в верхней панели)
   - `Execute SQL Script` → `Ctrl+Alt+X`
   - Подтвердить выполнение

4. **Проверить результат:**
   ```sql
   SELECT * FROM services;
   ```
   Должно показать 5 тестовых услуг.

### ✅ Шаг 6: Добавить реальные услуги FlaxTap

1. **Открыть update_services.sql:**
   - `File` → `Open File`
   - Выбрать: `C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty\database\update_services.sql`

2. **Выполнить скрипт:**
   - `Ctrl+Alt+X` или `Execute SQL Script`

3. **Проверить:**
   ```sql
   SELECT name, price FROM services ORDER BY price;
   ```
   Должно показать 9 услуг от 2500₽ до 4500₽.

### ✅ Шаг 7: Получить параметры для .env

1. Правой кнопкой на подключении → **Edit Connection**
2. Вкладка **Main**
3. Записать:
   - Host: `localhost`
   - Port: `5432`
   - Username: `postgres`
   - Password: [ваш пароль]

### ✅ Шаг 8: Обновить .env файл

Открыть: `C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty\.env`

Заменить строку 2:
```env
DATABASE_URL=postgresql://postgres:ВАШ_ПАРОЛЬ@localhost:5432/beauty_db
```

Например, если пароль `mypass123`:
```env
DATABASE_URL=postgresql://postgres:mypass123@localhost:5432/beauty_db
```

Сохранить (Ctrl+S)

---

## 🧪 Проверка подключения

После настройки .env файла, проверьте подключение:

```bash
cd C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty
.\venv\Scripts\activate
python test_db_connection.py
```

Должно показать:
```
✅ УСПЕШНО! PostgreSQL подключен!
📊 Версия: PostgreSQL 15.x
```

---

## 🚀 Запуск проекта

После успешной настройки БД:

```bash
cd C:\Users\Ксения\Yandex.Disk\PythonProjects\web_projects\beauty
.\venv\Scripts\activate
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Открыть в браузере: http://localhost:8000

---

## ❓ Проблемы и решения

### PostgreSQL не запускается

**Проверить:**
1. Установлен ли PostgreSQL?
   - Win+R → `services.msc` → поиск "postgresql"
   - Если не найден → установить с https://www.postgresql.org/download/windows/

2. Порт 5432 занят?
   ```powershell
   netstat -an | findstr "5432"
   ```
   Если занят → изменить порт в настройках PostgreSQL

### Забыл пароль от PostgreSQL

**Решение 1: Посмотреть в DBeaver**
1. Найти существующее подключение в DBeaver
2. Правой кнопкой → Edit Connection
3. В поле Password нажать "Show"

**Решение 2: Сбросить пароль**
1. Найти файл `pg_hba.conf` (обычно в `C:\Program Files\PostgreSQL\15\data\`)
2. Изменить метод аутентификации на `trust`
3. Перезапустить PostgreSQL
4. Подключиться без пароля
5. Изменить пароль:
   ```sql
   ALTER USER postgres PASSWORD 'новый_пароль';
   ```
6. Вернуть метод на `md5` в `pg_hba.conf`
7. Перезапустить PostgreSQL

### База данных не создается

**Проверить права:**
```sql
SELECT current_user;
-- Должно показать: postgres

SELECT * FROM pg_roles WHERE rolname = 'postgres';
-- Проверить что rolsuper = true
```

---

## 📚 Полезные SQL команды

### Проверить существующие базы данных
```sql
SELECT datname FROM pg_database;
```

### Проверить таблицы в beauty_db
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

### Проверить услуги
```sql
SELECT id, name, price, duration_minutes
FROM services
ORDER BY price;
```

### Проверить клиентов
```sql
SELECT * FROM clients;
```

### Удалить и пересоздать БД (если нужно начать заново)
```sql
-- ВНИМАНИЕ: Удалит ВСЕ данные!
DROP DATABASE IF EXISTS beauty_db;

CREATE DATABASE beauty_db
    WITH OWNER = postgres
    ENCODING = 'UTF8'
    CONNECTION LIMIT = -1;
```

---

**Готово! После выполнения всех шагов переходите к [START_HERE.md](START_HERE.md) для запуска проекта.**
