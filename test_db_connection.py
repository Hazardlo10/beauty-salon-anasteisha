"""
Тестовый скрипт для проверки подключения к PostgreSQL
Запустить: python test_db_connection.py
"""
import psycopg2
from psycopg2 import OperationalError

def test_connection():
    """Проверка подключения к PostgreSQL"""

    # Настройки подключения
    host = "localhost"
    port = "5432"
    database = "postgres"  # Стандартная БД для проверки
    user = "postgres"
    password = input("Введите пароль от PostgreSQL: ")

    try:
        # Попытка подключения
        connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

        # Получение версии PostgreSQL
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()

        print("\n✅ УСПЕШНО! PostgreSQL подключен!")
        print(f"📊 Версия: {db_version[0]}")
        print(f"\n🔗 Строка подключения для .env:")
        print(f"DATABASE_URL=postgresql://{user}:{password}@{host}:{port}/beauty_db")

        cursor.close()
        connection.close()

    except OperationalError as e:
        print("\n❌ ОШИБКА подключения к PostgreSQL!")
        print(f"Детали: {e}")
        print("\n💡 Возможные причины:")
        print("1. PostgreSQL не запущен (проверьте через DBeaver или Services)")
        print("2. Неправильный пароль")
        print("3. PostgreSQL слушает на другом порту (не 5432)")
        print("4. Firewall блокирует подключение")

if __name__ == "__main__":
    print("🔍 Проверка подключения к PostgreSQL...")
    print("=" * 50)
    test_connection()
