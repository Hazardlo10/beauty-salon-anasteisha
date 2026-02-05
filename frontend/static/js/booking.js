/**
 * Booking Widget - Anasteisha Beauty Salon
 * Пошаговый виджет онлайн-записи
 */

class BookingWidget {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 3;  // Упрощено: Услуга → Дата+Время → Данные
        this.selectedService = null;
        this.selectedDate = null;
        this.selectedTime = null;
        this.services = [];
        this.availableSlots = [];

        // Загрузка сохранённых данных клиента
        this.savedClient = this.loadSavedClient();

        this.init();
    }

    loadSavedClient() {
        try {
            const saved = localStorage.getItem('anasteisha_client');
            return saved ? JSON.parse(saved) : null;
        } catch {
            return null;
        }
    }

    saveClient(name, phone, email) {
        try {
            localStorage.setItem('anasteisha_client', JSON.stringify({ name, phone, email }));
        } catch {}
    }

    async init() {
        await this.loadServices();
        this.renderWidget();
        this.setupEventListeners();
    }

    // Справочник описаний услуг
    getServiceDescriptions() {
        return {
            'Атравматическая чистка лица': 'Деликатная процедура глубокого очищения без механического воздействия. Использует энзимные и кислотные пилинги. Идеально для чувствительной, куперозной кожи и при акне.',
            'Лифтинг-омоложение лица': 'Интенсивная антивозрастная процедура с пептидными комплексами. Стимулирует выработку коллагена и эластина, подтягивает овал лица, разглаживает морщины.',
            'Липосомальное обновление кожи': 'Инновационная доставка активных веществ в глубокие слои кожи с помощью липосом. Интенсивное увлажнение, питание и регенерация клеток.',
            'Ферментотерапия лица': 'Мягкий энзимный пилинг на основе натуральных ферментов папайи и ананаса. Деликатно растворяет ороговевшие клетки, очищает поры, выравнивает тон кожи.',
            'Безынъекционный ботокс лица': 'Процедура с аргирелином и пептидным комплексом. Расслабляет мимические мышцы, разглаживает морщины лба и межбровья. Безопасная альтернатива инъекциям.',
            'Атравматическая чистка спины': 'Профессиональное очищение кожи спины от высыпаний и воспалений. Включает распаривание, энзимный пилинг, бережную экстракцию, успокаивающую маску.',
            'Лифтинг шеи и декольте': 'Специальный уход за деликатной зоной шеи и декольте. Устраняет дряблость, пигментацию, мелкие морщины. Коллагеновые маски и моделирующий массаж.',
            'Обновление лица и декольте': 'Комплексная anti-age программа для лица и зоны декольте. Пилинг, сыворотки с гиалуроновой кислотой, коллагеновая маска и массаж.',
            'Ботокс лица и шеи': 'Расширенная безынъекционная процедура ботокс-эффекта для лица и шеи. Пептидные комплексы расслабляют мимику, лифтинг-маска подтягивает контуры.'
        };
    }

    async loadServices() {
        const descriptions = this.getServiceDescriptions();

        try {
            const response = await fetch('/api/services');
            if (response.ok) {
                this.services = await response.json();
                // Дополняем услуги описаниями, если они отсутствуют
                this.services = this.services.map(service => {
                    if (!service.description) {
                        service.description = descriptions[service.name] || 'Профессиональная косметологическая процедура для красоты и здоровья вашей кожи.';
                    }
                    return service;
                });
            }
        } catch (error) {
            console.error('Error loading services:', error);
            // Fallback услуги если API недоступен
            this.services = [
                { id: 1, name: 'Атравматическая чистка лица', price: 2500, duration_minutes: 60, category: 'Лицо', description: descriptions['Атравматическая чистка лица'] },
                { id: 2, name: 'Лифтинг-омоложение лица', price: 2800, duration_minutes: 90, category: 'Лицо', description: descriptions['Лифтинг-омоложение лица'] },
                { id: 3, name: 'Липосомальное обновление кожи', price: 2800, duration_minutes: 90, category: 'Лицо', description: descriptions['Липосомальное обновление кожи'] },
                { id: 4, name: 'Ферментотерапия лица', price: 2800, duration_minutes: 75, category: 'Лицо', description: descriptions['Ферментотерапия лица'] },
                { id: 5, name: 'Безынъекционный ботокс лица', price: 2800, duration_minutes: 90, category: 'Лицо', description: descriptions['Безынъекционный ботокс лица'] },
                { id: 6, name: 'Атравматическая чистка спины', price: 4500, duration_minutes: 90, category: 'Комплекс', description: descriptions['Атравматическая чистка спины'] },
                { id: 7, name: 'Лифтинг шеи и декольте', price: 3500, duration_minutes: 75, category: 'Комплекс', description: descriptions['Лифтинг шеи и декольте'] },
                { id: 8, name: 'Обновление лица и декольте', price: 3500, duration_minutes: 120, category: 'Комплекс', description: descriptions['Обновление лица и декольте'] },
                { id: 9, name: 'Ботокс лица и шеи', price: 3800, duration_minutes: 105, category: 'Комплекс', description: descriptions['Ботокс лица и шеи'] },
            ];
        }
    }

    renderWidget() {
        const container = document.getElementById('bookingWidget');
        if (!container) return;

        // Приветствие для повторных клиентов
        const welcomeBack = this.savedClient ? `
            <div class="welcome-back-banner">
                <i class="fas fa-heart"></i>
                <span>С возвращением, ${this.savedClient.name}!</span>
            </div>
        ` : '';

        container.innerHTML = `
            <div class="booking-widget">
                ${welcomeBack}

                <!-- Progress Steps - Упрощено до 3 шагов -->
                <div class="booking-progress">
                    <div class="progress-step active" data-step="1">
                        <span class="step-number">1</span>
                        <span class="step-label">Услуга</span>
                    </div>
                    <div class="progress-line"></div>
                    <div class="progress-step" data-step="2">
                        <span class="step-number">2</span>
                        <span class="step-label">Дата и время</span>
                    </div>
                    <div class="progress-line"></div>
                    <div class="progress-step" data-step="3">
                        <span class="step-number">3</span>
                        <span class="step-label">Контакты</span>
                    </div>
                </div>

                <!-- Step Content -->
                <div class="booking-steps">
                    <!-- Step 1: Service Selection -->
                    <div class="booking-step active" data-step="1">
                        <h3><i class="fas fa-spa"></i> Выберите услугу</h3>
                        <div class="services-list" id="servicesList"></div>
                    </div>

                    <!-- Step 2: Date + Time Selection (объединено) -->
                    <div class="booking-step" data-step="2">
                        <h3><i class="fas fa-calendar-alt"></i> Выберите дату и время</h3>
                        <div class="selected-service-info" id="selectedServiceInfo"></div>
                        <div class="datetime-selector">
                            <div class="calendar-container" id="calendarContainer"></div>
                            <div class="time-slots-container">
                                <div class="time-slots-header" id="timeSlotsHeader"></div>
                                <div class="time-slots" id="timeSlots"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 3: Contact Info -->
                    <div class="booking-step" data-step="3">
                        <h3><i class="fas fa-user"></i> Ваши данные</h3>
                        <div class="booking-summary" id="bookingSummary"></div>
                        <form class="contact-form" id="bookingContactForm">
                            <div class="form-group">
                                <label for="bookingName"><i class="fas fa-user"></i> Имя *</label>
                                <input type="text" id="bookingName" name="name" required
                                    placeholder="Введите ваше имя"
                                    value="${this.savedClient?.name || ''}">
                            </div>
                            <div class="form-group">
                                <label for="bookingPhone"><i class="fas fa-phone"></i> Телефон *</label>
                                <input type="tel" id="bookingPhone" name="phone" required
                                    placeholder="+7 (999) 999-99-99"
                                    value="${this.savedClient?.phone || ''}">
                            </div>
                            <div class="form-group">
                                <label for="bookingEmail"><i class="fas fa-envelope"></i> Email</label>
                                <input type="email" id="bookingEmail" name="email"
                                    placeholder="your@email.com"
                                    value="${this.savedClient?.email || ''}">
                            </div>
                            <div class="form-group">
                                <label for="bookingNotes"><i class="fas fa-comment"></i> Пожелания</label>
                                <textarea id="bookingNotes" name="notes" placeholder="Дополнительная информация..."></textarea>
                            </div>
                            <div class="form-group checkbox-group">
                                <label class="checkbox-label">
                                    <input type="checkbox" id="rememberMe" checked>
                                    <span>Запомнить мои данные</span>
                                </label>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Navigation Buttons -->
                <div class="booking-nav">
                    <button class="btn btn-outline booking-prev" id="prevBtn" style="display: none;">
                        <i class="fas fa-arrow-left"></i> Назад
                    </button>
                    <button class="btn btn-primary booking-next" id="nextBtn" disabled>
                        Далее <i class="fas fa-arrow-right"></i>
                    </button>
                    <button class="btn btn-primary booking-submit" id="submitBtn" style="display: none;">
                        <i class="fas fa-check"></i> Записаться
                    </button>
                </div>
            </div>
        `;

        this.renderServices();
    }

    renderServices() {
        const container = document.getElementById('servicesList');
        if (!container) return;

        // Иконки для разных типов услуг
        const serviceIcons = {
            'чистка': 'fa-leaf',
            'лифтинг': 'fa-arrow-up',
            'обновление': 'fa-sync-alt',
            'ферментотерапия': 'fa-flask',
            'ботокс': 'fa-star',
            'default': 'fa-spa'
        };

        const getIcon = (name) => {
            const nameLower = name.toLowerCase();
            for (const [key, icon] of Object.entries(serviceIcons)) {
                if (nameLower.includes(key)) return icon;
            }
            return serviceIcons.default;
        };

        // Группируем по категориям
        const categories = {};
        this.services.forEach(service => {
            const cat = service.category || 'Другое';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(service);
        });

        let html = '';
        for (const [category, services] of Object.entries(categories)) {
            const catIcon = category === 'Лицо' ? 'fa-face-smile' : 'fa-spa';
            // Категории свёрнуты по умолчанию
            html += `<div class="service-category-widget collapsed">
                <div class="category-header" data-category="${category}">
                    <h4><i class="fas ${catIcon}"></i> ${category}</h4>
                    <span class="category-count">${services.length} услуг</span>
                    <i class="fas fa-chevron-down category-toggle"></i>
                </div>
                <div class="services-options">`;

            services.forEach(service => {
                const icon = getIcon(service.name);
                html += `
                    <div class="service-option" data-service-id="${service.id}">
                        <div class="service-option-icon">
                            <i class="fas ${icon}"></i>
                        </div>
                        <div class="service-option-info">
                            <span class="service-name">${service.name}</span>
                            <span class="service-price">${service.price.toLocaleString()} ₽ <span>• ${service.duration_minutes} мин</span></span>
                        </div>
                        <div class="service-option-check">
                            <i class="fas fa-check"></i>
                        </div>
                    </div>
                `;
            });

            html += '</div></div>';
        }

        container.innerHTML = html;
    }

    renderCalendar() {
        const container = document.getElementById('calendarContainer');
        if (!container) return;

        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getFullYear();

        // Генерируем календарь на текущий месяц
        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        const startingDay = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1; // Понедельник = 0

        const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                          'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
        const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

        let html = `
            <div class="calendar">
                <div class="calendar-header">
                    <button class="calendar-nav" id="prevMonth"><i class="fas fa-chevron-left"></i></button>
                    <span class="calendar-title">${monthNames[currentMonth]} ${currentYear}</span>
                    <button class="calendar-nav" id="nextMonth"><i class="fas fa-chevron-right"></i></button>
                </div>
                <div class="calendar-days">
                    ${dayNames.map(d => `<div class="day-name">${d}</div>`).join('')}
                </div>
                <div class="calendar-dates">
        `;

        // Пустые ячейки до первого дня
        for (let i = 0; i < startingDay; i++) {
            html += '<div class="calendar-date empty"></div>';
        }

        // Дни месяца
        const maxBookingDate = new Date();
        maxBookingDate.setDate(maxBookingDate.getDate() + 30);

        for (let day = 1; day <= lastDay.getDate(); day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateStr = this.formatDate(date);
            const isPast = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const isTooFar = date > maxBookingDate;
            const isToday = date.toDateString() === today.toDateString();

            let classes = 'calendar-date';
            if (isPast || isTooFar) classes += ' disabled';
            if (isToday) classes += ' today';

            html += `<div class="${classes}" data-date="${dateStr}">${day}</div>`;
        }

        html += '</div></div>';
        container.innerHTML = html;
    }

    async loadTimeSlots(dateStr) {
        const container = document.getElementById('timeSlots');
        const header = document.getElementById('timeSlotsHeader');
        container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';

        // Показать выбранную дату в заголовке
        const dateObj = new Date(dateStr);
        const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
        if (header) {
            header.innerHTML = `<h4><i class="fas fa-clock"></i> ${dateObj.getDate()} ${monthNames[dateObj.getMonth()]}, ${dayNames[dateObj.getDay()]}</h4>`;
        }

        try {
            const serviceId = this.selectedService?.id || '';
            const response = await fetch(`/api/schedule/${dateStr}?service_id=${serviceId}`);

            if (!response.ok) {
                throw new Error('Failed to load schedule');
            }

            const data = await response.json();

            if (!data.is_working_day) {
                container.innerHTML = '<div class="no-slots">Выходной день</div>';
                return;
            }

            const availableSlots = data.slots.filter(s => s.available);

            if (availableSlots.length === 0) {
                container.innerHTML = '<div class="no-slots">Нет свободных слотов на эту дату</div>';
                return;
            }

            // Группируем слоты по времени суток
            const morning = availableSlots.filter(s => parseInt(s.time.split(':')[0]) < 12);
            const afternoon = availableSlots.filter(s => {
                const hour = parseInt(s.time.split(':')[0]);
                return hour >= 12 && hour < 17;
            });
            const evening = availableSlots.filter(s => parseInt(s.time.split(':')[0]) >= 17);

            let html = '<div class="time-groups">';

            if (morning.length > 0) {
                html += `
                    <div class="time-group">
                        <h5><i class="fas fa-sun"></i> Утро</h5>
                        <div class="time-options">
                            ${morning.map(s => `<div class="time-option" data-time="${s.time}">${s.time}</div>`).join('')}
                        </div>
                    </div>
                `;
            }

            if (afternoon.length > 0) {
                html += `
                    <div class="time-group">
                        <h5><i class="fas fa-cloud-sun"></i> День</h5>
                        <div class="time-options">
                            ${afternoon.map(s => `<div class="time-option" data-time="${s.time}">${s.time}</div>`).join('')}
                        </div>
                    </div>
                `;
            }

            if (evening.length > 0) {
                html += `
                    <div class="time-group">
                        <h5><i class="fas fa-moon"></i> Вечер</h5>
                        <div class="time-options">
                            ${evening.map(s => `<div class="time-option" data-time="${s.time}">${s.time}</div>`).join('')}
                        </div>
                    </div>
                `;
            }

            html += '</div>';
            container.innerHTML = html;

        } catch (error) {
            console.error('Error loading time slots:', error);
            container.innerHTML = '<div class="error">Не удалось загрузить расписание. Попробуйте позже.</div>';
        }
    }

    updateSelectedInfo() {
        const container = document.getElementById('selectedInfo');
        if (!container) return;

        const dateObj = new Date(this.selectedDate);
        const dayNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

        container.innerHTML = `
            <div class="selected-service">
                <i class="fas fa-spa"></i>
                <span>${this.selectedService?.name || 'Не выбрано'}</span>
            </div>
            <div class="selected-date">
                <i class="fas fa-calendar"></i>
                <span>${dateObj.getDate()} ${monthNames[dateObj.getMonth()]}, ${dayNames[dateObj.getDay()]}</span>
            </div>
        `;
    }

    updateSummary() {
        const container = document.getElementById('bookingSummary');
        if (!container) return;

        const dateObj = new Date(this.selectedDate);
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

        container.innerHTML = `
            <div class="summary-card">
                <div class="summary-row">
                    <span class="summary-label"><i class="fas fa-spa"></i> Услуга:</span>
                    <span class="summary-value">${this.selectedService?.name}</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label"><i class="fas fa-calendar"></i> Дата:</span>
                    <span class="summary-value">${dateObj.getDate()} ${monthNames[dateObj.getMonth()]}</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label"><i class="fas fa-clock"></i> Время:</span>
                    <span class="summary-value">${this.selectedTime}</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label"><i class="fas fa-hourglass-half"></i> Длительность:</span>
                    <span class="summary-value">${this.selectedService?.duration_minutes} мин</span>
                </div>
                <div class="summary-row total">
                    <span class="summary-label"><i class="fas fa-ruble-sign"></i> Стоимость:</span>
                    <span class="summary-value">${this.selectedService?.price.toLocaleString()} ₽</span>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        // Category toggle (accordion)
        document.addEventListener('click', (e) => {
            const categoryHeader = e.target.closest('.category-header');
            if (categoryHeader) {
                const categoryWidget = categoryHeader.closest('.service-category-widget');
                if (categoryWidget) {
                    categoryWidget.classList.toggle('collapsed');
                }
                return;
            }

            // Service selection
            const serviceOption = e.target.closest('.service-option');
            if (serviceOption) {
                document.querySelectorAll('.service-option').forEach(el => el.classList.remove('selected'));
                serviceOption.classList.add('selected');
                const serviceId = parseInt(serviceOption.dataset.serviceId);
                this.selectedService = this.services.find(s => s.id === serviceId);
                this.updateNextButton();
            }

            // Date selection
            const dateCell = e.target.closest('.calendar-date:not(.disabled):not(.empty)');
            if (dateCell) {
                document.querySelectorAll('.calendar-date').forEach(el => el.classList.remove('selected'));
                dateCell.classList.add('selected');
                this.selectedDate = dateCell.dataset.date;
                this.selectedTime = null; // Сбрасываем выбранное время при смене даты
                this.loadTimeSlots(dateCell.dataset.date); // Загружаем слоты времени
                this.updateNextButton();
            }

            // Time selection
            const timeOption = e.target.closest('.time-option');
            if (timeOption) {
                document.querySelectorAll('.time-option').forEach(el => el.classList.remove('selected'));
                timeOption.classList.add('selected');
                this.selectedTime = timeOption.dataset.time;
                this.updateNextButton();
            }
        });

        // Navigation buttons
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.goToStep(this.currentStep - 1));
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.goToStep(this.currentStep + 1));
        }

        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitBooking());
        }

        // Phone formatting and validation
        const phoneInput = document.getElementById('bookingPhone');
        if (phoneInput) {
            phoneInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 0) {
                    if (value[0] === '8') value = '7' + value.slice(1);
                    if (value[0] !== '7') value = '7' + value;

                    let formatted = '+7';
                    if (value.length > 1) formatted += ' (' + value.slice(1, 4);
                    if (value.length > 4) formatted += ') ' + value.slice(4, 7);
                    if (value.length > 7) formatted += '-' + value.slice(7, 9);
                    if (value.length > 9) formatted += '-' + value.slice(9, 11);

                    e.target.value = formatted;
                }
                this.updateNextButton();
            });
        }

        // Name input - update button state
        const nameInput = document.getElementById('bookingName');
        if (nameInput) {
            nameInput.addEventListener('input', () => {
                this.updateNextButton();
            });
        }
    }

    goToStep(step) {
        if (step < 1 || step > this.totalSteps) return;

        // Validate current step before proceeding
        if (step > this.currentStep && !this.validateStep(this.currentStep)) {
            return;
        }

        this.currentStep = step;

        // Update progress
        document.querySelectorAll('.progress-step').forEach((el, index) => {
            el.classList.remove('active', 'completed');
            if (index + 1 < step) el.classList.add('completed');
            if (index + 1 === step) el.classList.add('active');
        });

        // Show current step
        document.querySelectorAll('.booking-step').forEach(el => {
            el.classList.remove('active');
            if (parseInt(el.dataset.step) === step) el.classList.add('active');
        });

        // Update navigation buttons
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        prevBtn.style.display = step > 1 ? 'flex' : 'none';
        nextBtn.style.display = step < this.totalSteps ? 'flex' : 'none';
        submitBtn.style.display = step === this.totalSteps ? 'flex' : 'none';

        // Load step-specific content (новая логика для 3 шагов)
        if (step === 2) {
            this.showSelectedServiceInfo();
            this.renderCalendar();
            // Показать заглушку для слотов времени
            const header = document.getElementById('timeSlotsHeader');
            const slots = document.getElementById('timeSlots');
            if (header) header.innerHTML = '<p class="select-date-hint"><i class="fas fa-hand-point-left"></i> Выберите дату</p>';
            if (slots) slots.innerHTML = '';
        } else if (step === 3) {
            this.updateSummary();
        }

        this.updateNextButton();
    }

    showSelectedServiceInfo() {
        const container = document.getElementById('selectedServiceInfo');
        if (!container || !this.selectedService) return;

        container.innerHTML = `
            <div class="selected-service-badge">
                <i class="fas fa-spa"></i>
                <span>${this.selectedService.name}</span>
                <span class="service-badge-price">${this.selectedService.price.toLocaleString()} ₽</span>
            </div>
        `;
    }

    validateStep(step) {
        switch (step) {
            case 1:
                return this.selectedService !== null;
            case 2:
                // Теперь нужны и дата, и время на одном шаге
                return this.selectedDate !== null && this.selectedTime !== null;
            case 3:
                const name = document.getElementById('bookingName')?.value;
                const phone = document.getElementById('bookingPhone')?.value;
                return name && phone;
            default:
                return true;
        }
    }

    updateNextButton() {
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (nextBtn) {
            nextBtn.disabled = !this.validateStep(this.currentStep);
        }

        if (submitBtn && this.currentStep === this.totalSteps) {
            const name = document.getElementById('bookingName')?.value;
            const phone = document.getElementById('bookingPhone')?.value;
            submitBtn.disabled = !(name && phone);
        }
    }

    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async submitBooking() {
        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';

        const clientName = document.getElementById('bookingName').value;
        const clientPhone = document.getElementById('bookingPhone').value;
        const clientEmail = document.getElementById('bookingEmail').value || null;

        const data = {
            service_id: this.selectedService.id,
            appointment_date: this.selectedDate,
            appointment_time: this.selectedTime,
            client_name: clientName,
            client_phone: clientPhone,
            client_email: clientEmail,
            notes: document.getElementById('bookingNotes').value || null
        };

        try {
            const response = await fetch('/api/appointments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.id) {
                // Сохранить данные клиента если отмечен чекбокс
                const rememberMe = document.getElementById('rememberMe')?.checked;
                if (rememberMe) {
                    this.saveClient(clientName, clientPhone, clientEmail);
                }
                this.showSuccess(result);
            } else {
                throw new Error(result.detail || 'Ошибка при создании записи');
            }
        } catch (error) {
            console.error('Booking error:', error);
            alert('Ошибка: ' + error.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Записаться';
        }
    }

    showSuccess(result) {
        // Отправляем цель в Яндекс.Метрику
        if (typeof ym !== 'undefined') {
            ym(window.YM_COUNTER_ID, 'reachGoal', 'booking_success', {
                service: this.selectedService?.name,
                price: this.selectedService?.price
            });
        }

        const dateObj = new Date(this.selectedDate);
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

        const container = document.getElementById('bookingWidget');
        container.innerHTML = `
            <div class="booking-success">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h3>Запись создана!</h3>
                <p>Ваша запись успешно оформлена. Мы свяжемся с вами для подтверждения.</p>

                <div class="success-details">
                    <div class="success-row">
                        <span class="label">Услуга:</span>
                        <span class="value">${this.selectedService.name}</span>
                    </div>
                    <div class="success-row">
                        <span class="label">Дата и время:</span>
                        <span class="value">${dateObj.getDate()} ${monthNames[dateObj.getMonth()]} в ${this.selectedTime}</span>
                    </div>
                    <div class="success-row">
                        <span class="label">Стоимость:</span>
                        <span class="value">${this.selectedService.price.toLocaleString()} ₽</span>
                    </div>
                    <div class="success-row">
                        <span class="label">Номер записи:</span>
                        <span class="value">#${result.id}</span>
                    </div>
                </div>

                <div class="success-actions">
                    <button class="btn btn-outline" onclick="closeBookingModal()">
                        <i class="fas fa-times"></i> Закрыть
                    </button>
                    <a href="/my-bookings.html" class="btn btn-primary">
                        <i class="fas fa-list"></i> Мои записи
                    </a>
                </div>

                <p class="success-note">
                    <i class="fas fa-info-circle"></i>
                    Вы можете отменить или перенести запись за 2 часа до назначенного времени
                </p>
            </div>
        `;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if widget container exists
    if (document.getElementById('bookingWidget')) {
        window.bookingWidgetInstance = new BookingWidget();
    }
});
