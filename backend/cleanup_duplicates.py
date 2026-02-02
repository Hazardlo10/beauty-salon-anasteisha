"""
Скрипт для удаления дублей записей
Запуск: python cleanup_duplicates.py
"""
from app.database import SessionLocal
from app.models.appointment import Appointment
from sqlalchemy import func

def cleanup_duplicates():
    db = SessionLocal()

    try:
        # Найти группы дублей
        duplicates = db.query(
            Appointment.client_id,
            Appointment.appointment_date,
            Appointment.appointment_time,
            func.min(Appointment.id).label('keep_id'),
            func.count(Appointment.id).label('count')
        ).filter(
            Appointment.status.in_(["pending", "confirmed"])
        ).group_by(
            Appointment.client_id,
            Appointment.appointment_date,
            Appointment.appointment_time
        ).having(func.count(Appointment.id) > 1).all()

        if not duplicates:
            print("Дублей не найдено!")
            return

        print(f"Найдено {len(duplicates)} групп дублей:")

        deleted_count = 0
        for dup in duplicates:
            # Получить все записи в группе дублей
            appointments = db.query(Appointment).filter(
                Appointment.client_id == dup.client_id,
                Appointment.appointment_date == dup.appointment_date,
                Appointment.appointment_time == dup.appointment_time,
                Appointment.status.in_(["pending", "confirmed"])
            ).order_by(Appointment.id).all()

            print(f"\n  Клиент {dup.client_id}, {dup.appointment_date} {dup.appointment_time}:")

            # Оставить первую запись, удалить остальные
            for i, apt in enumerate(appointments):
                if i == 0:
                    print(f"    ID {apt.id} - ОСТАВИТЬ (status: {apt.status})")
                else:
                    print(f"    ID {apt.id} - УДАЛИТЬ (status: {apt.status})")
                    db.delete(apt)
                    deleted_count += 1

        if deleted_count > 0:
            confirm = input(f"\nУдалить {deleted_count} дублей? (y/n): ")
            if confirm.lower() == 'y':
                db.commit()
                print(f"Удалено {deleted_count} дублей")
            else:
                db.rollback()
                print("Отменено")

    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicates()
