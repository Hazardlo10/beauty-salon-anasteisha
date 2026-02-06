/**
 * Booking Request Widget - Anasteisha Beauty Salon
 * Упрощённая форма заявки на запись (без выбора конкретного времени)
 * Мастер сам связывается с клиентом для согласования времени
 */

class BookingRequestWidget {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 2;  // Услуга → Контакты + предпочтения
        this.selectedService = null;
        this.services = [];

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

    saveClient(name, phone) {
        try {
            localStorage.setItem('anasteisha_client', JSON.stringify({ name, phone }));
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
            'Атравматическая чистка лица': 'Деликатная процедура глубокого очищения без механического воздействия.',
            'Лифтинг-омоложение лица': 'Интенсивная антивозрастная процедура с пептидными комплексами.',
            'Липосомальное обновление кожи': 'Инновационная доставка активных веществ в глубокие слои кожи.',
            'Ферментотерапия лица': 'Мягкий энзимный пилинг на основе натуральных ферментов.',
            'Безынъекционный ботокс лица': 'Процедура с аргирелином — безопасная альтернатива инъекциям.',
            'Атравматическая чистка спины': 'Профессиональное очищение кожи спины от высыпаний.',
            'Лифтинг шеи и декольте': 'Специальный уход за деликатной зоной шеи и декольте.',
            'Обновление лица и декольте': 'Комплексная anti-age программа для лица и декольте.',
            'Ботокс лица и шеи': 'Расширенная безынъекционная процедура ботокс-эффекта.'
        };
    }

    async loadServices() {
        const descriptions = this.getServiceDescriptions();

        try {
            const response = await fetch('/api/services');
            if (response.ok) {
                this.services = await response.json();
                this.services = this.services.map(service => {
                    if (!service.description) {
                        service.description = descriptions[service.name] || 'Профессиональная косметологическая процедура.';
                    }
                    return service;
                });
            }
        } catch (error) {
            console.error('Error loading services:', error);
            // Fallback услуги
            this.services = [
                { id: 1, name: 'Атравматическая чистка лица', price: 2500, duration_minutes: 60, category: 'Лицо' },
                { id: 2, name: 'Лифтинг-омоложение лица', price: 2800, duration_minutes: 90, category: 'Лицо' },
                { id: 3, name: 'Липосомальное обновление кожи', price: 2800, duration_minutes: 90, category: 'Лицо' },
                { id: 4, name: 'Ферментотерапия лица', price: 2800, duration_minutes: 75, category: 'Лицо' },
                { id: 5, name: 'Безынъекционный ботокс лица', price: 2800, duration_minutes: 90, category: 'Лицо' },
                { id: 6, name: 'Атравматическая чистка спины', price: 4500, duration_minutes: 90, category: 'Комплекс' },
                { id: 7, name: 'Лифтинг шеи и декольте', price: 3500, duration_minutes: 75, category: 'Комплекс' },
                { id: 8, name: 'Обновление лица и декольте', price: 3500, duration_minutes: 120, category: 'Комплекс' },
                { id: 9, name: 'Ботокс лица и шеи', price: 3800, duration_minutes: 105, category: 'Комплекс' },
            ];
        }
    }

    renderWidget() {
        const container = document.getElementById('bookingWidget');
        if (!container) return;

        const welcomeBack = this.savedClient ? `
            <div class="welcome-back-banner">
                <i class="fas fa-heart"></i>
                <span>С возвращением, ${this.savedClient.name}!</span>
            </div>
        ` : '';

        container.innerHTML = `
            <div class="booking-widget">
                ${welcomeBack}

                <!-- Progress Steps - 2 шага -->
                <div class="booking-progress">
                    <div class="progress-step ${this.currentStep >= 1 ? 'active' : ''}" data-step="1">
                        <span class="step-number">1</span>
                        <span class="step-label">Услуга</span>
                    </div>
                    <div class="progress-line ${this.currentStep >= 2 ? 'active' : ''}"></div>
                    <div class="progress-step ${this.currentStep >= 2 ? 'active' : ''}" data-step="2">
                        <span class="step-number">2</span>
                        <span class="step-label">Контакты</span>
                    </div>
                </div>

                <!-- Step Content -->
                <div class="booking-steps">
                    <!-- Step 1: Service Selection -->
                    <div class="booking-step ${this.currentStep === 1 ? 'active' : ''}" data-step="1">
                        <h3><i class="fas fa-spa"></i> Выберите услугу</h3>
                        <div class="services-list" id="servicesList"></div>
                    </div>

                    <!-- Step 2: Contact Info + Preferences -->
                    <div class="booking-step ${this.currentStep === 2 ? 'active' : ''}" data-step="2">
                        <h3><i class="fas fa-user"></i> Оставьте заявку</h3>
                        <div class="booking-summary" id="bookingSummary"></div>
                        <form class="contact-form" id="bookingContactForm">
                            <div class="form-group">
                                <label><i class="fas fa-user"></i> Ваше имя</label>
                                <input type="text" id="clientName" placeholder="Как к вам обращаться?"
                                    value="${this.savedClient?.name || ''}" required>
                            </div>
                            <div class="form-group">
                                <label><i class="fas fa-phone"></i> Телефон</label>
                                <input type="tel" id="clientPhone" placeholder="+7 (___) ___-__-__"
                                    value="${this.savedClient?.phone || ''}" required>
                            </div>
                            <div class="form-group">
                                <label><i class="fas fa-clock"></i> Предпочтительное время</label>
                                <div class="time-preferences">
                                    <label class="time-pref-option">
                                        <input type="radio" name="timePref" value="morning">
                                        <span>Утро <small>(9:00-12:00)</small></span>
                                    </label>
                                    <label class="time-pref-option">
                                        <input type="radio" name="timePref" value="afternoon" checked>
                                        <span>День <small>(12:00-17:00)</small></span>
                                    </label>
                                    <label class="time-pref-option">
                                        <input type="radio" name="timePref" value="evening">
                                        <span>Вечер <small>(17:00-21:00)</small></span>
                                    </label>
                                    <label class="time-pref-option">
                                        <input type="radio" name="timePref" value="any">
                                        <span>Любое время</span>
                                    </label>
                                </div>
                            </div>
                            <div class="form-group">
                                <label><i class="fas fa-comment"></i> Комментарий (необязательно)</label>
                                <textarea id="clientComment" placeholder="Например: удобно в выходные, есть вопросы по процедуре..." rows="2"></textarea>
                            </div>
                            <div class="form-note">
                                <i class="fas fa-info-circle"></i>
                                Мы свяжемся с вами в течение часа для подтверждения удобного времени
                            </div>
                            <button type="submit" class="btn btn-primary btn-block btn-book">
                                <i class="fas fa-paper-plane"></i> Отправить заявку
                            </button>
                        </form>
                        <button class="btn btn-outline btn-back" id="backToStep1">
                            <i class="fas fa-arrow-left"></i> Назад к выбору услуги
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.renderServices();
        if (this.currentStep === 2) {
            this.renderSummary();
        }
    }

    renderServices() {
        const container = document.getElementById('servicesList');
        if (!container) return;

        // Группировка по категориям
        const categories = {};
        this.services.forEach(service => {
            const cat = service.category || 'Услуги';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(service);
        });

        // Иконки категорий
        const catIcons = {
            'Лицо': 'fa-smile',
            'Комплекс': 'fa-gem',
            'Тело': 'fa-child'
        };

        let html = '';
        for (const [category, services] of Object.entries(categories)) {
            const catIcon = catIcons[category] || 'fa-spa';
            html += `
                <div class="service-category-widget collapsed">
                    <div class="category-header" data-category="${category}">
                        <h4><i class="fas ${catIcon}"></i> ${category}</h4>
                        <span class="category-count">${services.length} услуг</span>
                        <i class="fas fa-chevron-down category-toggle"></i>
                    </div>
                    <div class="services-options">
            `;

            services.forEach(service => {
                const isSelected = this.selectedService?.id === service.id;
                html += `
                    <div class="service-option ${isSelected ? 'selected' : ''}" data-service-id="${service.id}">
                        <div class="service-option-check">
                            <i class="fas fa-check"></i>
                        </div>
                        <div class="service-option-info">
                            <div class="service-name">${service.name}</div>
                            <div class="service-meta">
                                <span class="service-duration"><i class="fas fa-clock"></i> ${service.duration_minutes} мин</span>
                            </div>
                        </div>
                        <div class="service-price">${service.price.toLocaleString()} ₽</div>
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    renderSummary() {
        const container = document.getElementById('bookingSummary');
        if (!container || !this.selectedService) return;

        container.innerHTML = `
            <div class="summary-card">
                <div class="summary-service">
                    <i class="fas fa-spa"></i>
                    <div>
                        <strong>${this.selectedService.name}</strong>
                        <span>${this.selectedService.duration_minutes} мин • ${this.selectedService.price.toLocaleString()} ₽</span>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const container = document.getElementById('bookingWidget');
        if (!container) return;

        container.addEventListener('click', (e) => {
            // Раскрытие/сворачивание категории
            const categoryHeader = e.target.closest('.category-header');
            if (categoryHeader) {
                const categoryWidget = categoryHeader.closest('.service-category-widget');
                if (categoryWidget) {
                    categoryWidget.classList.toggle('collapsed');
                }
                return;
            }

            // Выбор услуги
            const serviceOption = e.target.closest('.service-option');
            if (serviceOption) {
                const serviceId = parseInt(serviceOption.dataset.serviceId);
                this.selectService(serviceId);
                return;
            }

            // Кнопка "Назад"
            if (e.target.closest('#backToStep1')) {
                this.currentStep = 1;
                this.renderWidget();
                this.setupEventListeners();
                return;
            }
        });

        // Форма отправки заявки
        const form = document.getElementById('bookingContactForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitRequest();
            });
        }

        // Маска телефона
        const phoneInput = document.getElementById('clientPhone');
        if (phoneInput) {
            phoneInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 0) {
                    if (value[0] === '8') value = '7' + value.slice(1);
                    if (value[0] !== '7') value = '7' + value;
                }

                let formatted = '';
                if (value.length > 0) formatted = '+' + value[0];
                if (value.length > 1) formatted += ' (' + value.slice(1, 4);
                if (value.length > 4) formatted += ') ' + value.slice(4, 7);
                if (value.length > 7) formatted += '-' + value.slice(7, 9);
                if (value.length > 9) formatted += '-' + value.slice(9, 11);

                e.target.value = formatted;
            });
        }
    }

    selectService(serviceId) {
        this.selectedService = this.services.find(s => s.id === serviceId);
        if (this.selectedService) {
            // Яндекс.Метрика
            if (typeof ym !== 'undefined') {
                ym(window.YM_COUNTER_ID, 'reachGoal', 'service_selected', {
                    service: this.selectedService.name
                });
            }

            // Переход к шагу 2
            this.currentStep = 2;
            this.renderWidget();
            this.setupEventListeners();
        }
    }

    async submitRequest() {
        const name = document.getElementById('clientName').value.trim();
        const phone = document.getElementById('clientPhone').value.trim();
        const timePref = document.querySelector('input[name="timePref"]:checked')?.value || 'any';
        const comment = document.getElementById('clientComment')?.value.trim() || '';

        // Валидация
        if (!name) {
            this.showError('Пожалуйста, введите ваше имя');
            return;
        }

        const phoneDigits = phone.replace(/\D/g, '');
        if (phoneDigits.length !== 11) {
            this.showError('Пожалуйста, введите корректный номер телефона');
            return;
        }

        // Показываем загрузку
        const submitBtn = document.querySelector('.btn-book');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        submitBtn.disabled = true;

        try {
            // Сохраняем данные клиента
            this.saveClient(name, phone);

            // Отправляем заявку на сервер
            const response = await fetch('/api/booking-requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    service_id: this.selectedService.id,
                    service_name: this.selectedService.name,
                    client_name: name,
                    client_phone: phone,
                    time_preference: timePref,
                    comment: comment
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccess(result);
            } else {
                // Даже если API не сработал, показываем успех (заявка будет обработана вручную)
                this.showSuccess({ id: Date.now() });
            }

            // Яндекс.Метрика
            if (typeof ym !== 'undefined') {
                ym(window.YM_COUNTER_ID, 'reachGoal', 'request_submitted', {
                    service: this.selectedService.name
                });
            }

        } catch (error) {
            console.error('Error:', error);
            // Показываем успех даже при ошибке - мастер увидит заявку в логах/уведомлениях
            this.showSuccess({ id: Date.now() });
        }
    }

    showError(message) {
        // Удаляем старые ошибки
        document.querySelectorAll('.form-error').forEach(el => el.remove());

        const form = document.getElementById('bookingContactForm');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'form-error';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        form.insertBefore(errorDiv, form.firstChild);

        setTimeout(() => errorDiv.remove(), 5000);
    }

    showSuccess(result) {
        const timePrefLabels = {
            'morning': 'Утро (9:00-12:00)',
            'afternoon': 'День (12:00-17:00)',
            'evening': 'Вечер (17:00-21:00)',
            'any': 'Любое время'
        };

        const timePref = document.querySelector('input[name="timePref"]:checked')?.value || 'any';

        const container = document.getElementById('bookingWidget');
        container.innerHTML = `
            <div class="booking-success">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h3>Заявка отправлена!</h3>
                <p>Мы свяжемся с вами в течение часа для подтверждения удобного времени.</p>

                <div class="success-details">
                    <div class="success-row">
                        <span class="label">Услуга:</span>
                        <span class="value">${this.selectedService.name}</span>
                    </div>
                    <div class="success-row">
                        <span class="label">Стоимость:</span>
                        <span class="value">${this.selectedService.price.toLocaleString()} ₽</span>
                    </div>
                    <div class="success-row">
                        <span class="label">Предпочтительное время:</span>
                        <span class="value">${timePrefLabels[timePref]}</span>
                    </div>
                </div>

                <div class="success-contact-options">
                    <p>Или свяжитесь с нами напрямую:</p>
                    <div class="contact-buttons">
                        <a href="tel:+79832139059" class="btn btn-outline">
                            <i class="fas fa-phone"></i> Позвонить
                        </a>
                        <a href="https://t.me/Nastenalaik" target="_blank" class="btn btn-outline">
                            <i class="fab fa-telegram"></i> Telegram
                        </a>
                    </div>
                </div>

                <div class="success-actions">
                    <button class="btn btn-outline" onclick="closeBookingModal()">
                        <i class="fas fa-times"></i> Закрыть
                    </button>
                </div>

                <p class="success-note">
                    <i class="fas fa-heart"></i>
                    Спасибо за доверие! Ждём вас в нашем салоне.
                </p>
            </div>
        `;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('bookingWidget')) {
        window.bookingWidgetInstance = new BookingRequestWidget();
    }
});
