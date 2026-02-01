-- Схема базы данных для системы онлайн-записи косметологического кабинета

-- Клиенты
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(100),
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    date_of_birth DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Услуги
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    category VARCHAR(50), -- 'уход за лицом', 'массаж', 'инъекции' и т.д.
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Записи на прием
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    service_id INTEGER REFERENCES services(id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'completed', 'cancelled', 'no_show'
    duration_minutes INTEGER NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'unpaid', -- 'unpaid', 'paid', 'refunded'
    payment_method VARCHAR(20), -- 'cash', 'card', 'online'
    notes TEXT,
    reminder_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_appointment UNIQUE (appointment_date, appointment_time)
);

-- История посещений (для аналитики)
CREATE TABLE visit_history (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    appointment_id INTEGER REFERENCES appointments(id),
    service_id INTEGER REFERENCES services(id),
    visit_date TIMESTAMP NOT NULL,
    notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Расписание работы
CREATE TABLE work_schedule (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0 = понедельник
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_working_day BOOLEAN DEFAULT true
);

-- Выходные дни и исключения
CREATE TABLE holidays (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    description VARCHAR(255),
    is_working BOOLEAN DEFAULT false
);

-- Платежи
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER REFERENCES appointments(id),
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'pending',
    transaction_id VARCHAR(100),
    payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Уведомления (лог отправленных уведомлений)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER REFERENCES appointments(id),
    notification_type VARCHAR(20) NOT NULL, -- 'telegram', 'sms', 'email'
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent' -- 'sent', 'failed', 'delivered'
);

-- Промокоды и скидки
CREATE TABLE promo_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_type VARCHAR(10) NOT NULL, -- 'percent' или 'fixed'
    discount_value DECIMAL(10, 2) NOT NULL,
    valid_from DATE,
    valid_until DATE,
    max_uses INTEGER,
    current_uses INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Админ-пользователи
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'admin', -- 'admin', 'super_admin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_client ON appointments(client_id);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_telegram ON clients(telegram_id);

-- Триггер для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Начальные данные для расписания (Пн-Пт: 9:00-18:00, Сб-Вс: выходные)
INSERT INTO work_schedule (day_of_week, start_time, end_time, is_working_day) VALUES
(0, '09:00', '18:00', true),  -- Понедельник
(1, '09:00', '18:00', true),  -- Вторник
(2, '09:00', '18:00', true),  -- Среда
(3, '09:00', '18:00', true),  -- Четверг
(4, '09:00', '18:00', true),  -- Пятница
(5, '10:00', '15:00', true),  -- Суббота
(6, '00:00', '00:00', false); -- Воскресенье

-- Примеры услуг
INSERT INTO services (name, description, duration_minutes, price, category) VALUES
('Чистка лица', 'Глубокая очистка пор, удаление комедонов', 60, 3500.00, 'Уход за лицом'),
('Массаж лица', 'Лимфодренажный массаж для омоложения', 45, 2500.00, 'Массаж'),
('Пилинг', 'Химический пилинг для обновления кожи', 50, 4000.00, 'Уход за лицом'),
('Ботокс', 'Инъекции ботулотоксина', 30, 8000.00, 'Инъекции'),
('Биоревитализация', 'Инъекции гиалуроновой кислоты', 40, 12000.00, 'Инъекции');
