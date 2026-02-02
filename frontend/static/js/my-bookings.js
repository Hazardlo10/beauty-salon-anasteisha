/**
 * My Bookings Page - Anasteisha Beauty Salon
 * Страница просмотра и управления записями клиента
 */

class MyBookingsPage {
    constructor() {
        this.currentPhone = null;
        this.appointments = [];
        this.selectedAppointment = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initTheme();

        // Проверяем сохранённый телефон
        const savedPhone = localStorage.getItem('booking_phone');
        if (savedPhone) {
            document.getElementById('searchPhone').value = savedPhone;
        }
    }

    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const newTheme = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
            });
        }
    }

    setupEventListeners() {
        // Phone search form
        const searchForm = document.getElementById('phoneSearchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchBookings();
            });
        }

        // Phone input formatting
        const phoneInput = document.getElementById('searchPhone');
        if (phoneInput) {
            phoneInput.addEventListener('input', (e) => {
                this.formatPhoneInput(e.target);
            });
        }

        // Change phone button
        const changePhoneBtn = document.getElementById('changePhoneBtn');
        if (changePhoneBtn) {
            changePhoneBtn.addEventListener('click', () => {
                this.showPhoneSearch();
            });
        }

        // Cancel confirmation
        const confirmCancelBtn = document.getElementById('confirmCancelBtn');
        if (confirmCancelBtn) {
            confirmCancelBtn.addEventListener('click', () => {
                this.cancelAppointment();
            });
        }
    }

    formatPhoneInput(input) {
        let value = input.value.replace(/\D/g, '');
        if (value.length > 0) {
            if (value[0] === '8') value = '7' + value.slice(1);
            if (value[0] !== '7') value = '7' + value;

            let formatted = '+7';
            if (value.length > 1) formatted += ' (' + value.slice(1, 4);
            if (value.length > 4) formatted += ') ' + value.slice(4, 7);
            if (value.length > 7) formatted += '-' + value.slice(7, 9);
            if (value.length > 9) formatted += '-' + value.slice(9, 11);

            input.value = formatted;
        }
    }

    async searchBookings() {
        const phone = document.getElementById('searchPhone').value;
        if (!phone || phone.length < 16) {
            alert('Введите корректный номер телефона');
            return;
        }

        this.currentPhone = phone;
        localStorage.setItem('booking_phone', phone);

        const bookingsList = document.getElementById('bookingsList');
        bookingsList.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';

        // Show bookings container
        document.getElementById('phoneSearchCard').style.display = 'none';
        document.getElementById('bookingsContainer').style.display = 'block';

        try {
            const response = await fetch(`/api/appointments/my?phone=${encodeURIComponent(phone)}`);
            const data = await response.json();

            if (response.ok) {
                this.appointments = data;
                this.renderBookings();
            } else {
                throw new Error(data.detail || 'Ошибка загрузки');
            }
        } catch (error) {
            console.error('Error loading bookings:', error);
            bookingsList.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Не удалось загрузить записи. Попробуйте позже.</p>
                </div>
            `;
        }
    }

    renderBookings() {
        const container = document.getElementById('bookingsList');

        if (this.appointments.length === 0) {
            container.innerHTML = `
                <div class="no-bookings">
                    <i class="fas fa-calendar-times"></i>
                    <h3>Записей не найдено</h3>
                    <p>По данному номеру телефона записей не найдено</p>
                    <a href="/#booking" class="btn btn-primary">
                        <i class="fas fa-plus"></i> Записаться
                    </a>
                </div>
            `;
            return;
        }

        // Группируем записи по статусу
        const upcoming = this.appointments.filter(a =>
            ['pending', 'confirmed'].includes(a.status) && new Date(a.appointment_date) >= new Date().setHours(0,0,0,0)
        );
        const past = this.appointments.filter(a =>
            !['pending', 'confirmed'].includes(a.status) || new Date(a.appointment_date) < new Date().setHours(0,0,0,0)
        );

        let html = '';

        if (upcoming.length > 0) {
            html += '<div class="bookings-section"><h3><i class="fas fa-clock"></i> Предстоящие записи</h3>';
            html += upcoming.map(apt => this.renderBookingCard(apt, true)).join('');
            html += '</div>';
        }

        if (past.length > 0) {
            html += '<div class="bookings-section"><h3><i class="fas fa-history"></i> История записей</h3>';
            html += past.map(apt => this.renderBookingCard(apt, false)).join('');
            html += '</div>';
        }

        container.innerHTML = html;

        // Add event listeners to action buttons
        this.attachCardEventListeners();
    }

    renderBookingCard(appointment, isUpcoming) {
        const date = new Date(appointment.appointment_date);
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
        const dayNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];

        const statusLabels = {
            'pending': { text: 'Ожидает подтверждения', class: 'pending', icon: 'clock' },
            'confirmed': { text: 'Подтверждена', class: 'confirmed', icon: 'check-circle' },
            'completed': { text: 'Завершена', class: 'completed', icon: 'check-double' },
            'cancelled': { text: 'Отменена', class: 'cancelled', icon: 'times-circle' },
            'no_show': { text: 'Неявка', class: 'no-show', icon: 'user-slash' }
        };

        const status = statusLabels[appointment.status] || { text: appointment.status, class: '', icon: 'question' };

        return `
            <div class="booking-card ${status.class}">
                <div class="booking-card-header">
                    <div class="booking-date">
                        <span class="date-day">${date.getDate()}</span>
                        <span class="date-month">${monthNames[date.getMonth()]}</span>
                        <span class="date-weekday">${dayNames[date.getDay()]}</span>
                    </div>
                    <div class="booking-time">
                        <i class="fas fa-clock"></i>
                        <span>${appointment.appointment_time}</span>
                    </div>
                    <div class="booking-status status-${status.class}">
                        <i class="fas fa-${status.icon}"></i>
                        <span>${status.text}</span>
                    </div>
                </div>

                <div class="booking-card-body">
                    <div class="booking-service">
                        <i class="fas fa-spa"></i>
                        <span>${appointment.service_name}</span>
                    </div>
                    <div class="booking-details">
                        <span class="booking-duration">
                            <i class="fas fa-hourglass-half"></i> ${appointment.duration_minutes} мин
                        </span>
                        <span class="booking-price">
                            <i class="fas fa-ruble-sign"></i> ${appointment.total_price.toLocaleString()} ₽
                        </span>
                    </div>
                </div>

                ${isUpcoming && (appointment.can_cancel || appointment.can_reschedule) ? `
                <div class="booking-card-actions">
                    ${appointment.can_reschedule ? `
                        <button class="btn btn-outline btn-sm reschedule-btn" data-id="${appointment.id}">
                            <i class="fas fa-calendar-alt"></i> Перенести
                        </button>
                    ` : ''}
                    ${appointment.can_cancel ? `
                        <button class="btn btn-outline btn-sm btn-danger cancel-btn" data-id="${appointment.id}">
                            <i class="fas fa-times"></i> Отменить
                        </button>
                    ` : ''}
                </div>
                ` : ''}

                <div class="booking-card-footer">
                    <span class="booking-id">Запись #${appointment.id}</span>
                    <span class="booking-created">Создана: ${appointment.created_at}</span>
                </div>
            </div>
        `;
    }

    attachCardEventListeners() {
        // Cancel buttons
        document.querySelectorAll('.cancel-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                this.selectedAppointment = this.appointments.find(a => a.id === id);
                this.showCancelModal();
            });
        });

        // Reschedule buttons
        document.querySelectorAll('.reschedule-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                this.selectedAppointment = this.appointments.find(a => a.id === id);
                this.showRescheduleModal();
            });
        });
    }

    showPhoneSearch() {
        document.getElementById('phoneSearchCard').style.display = 'block';
        document.getElementById('bookingsContainer').style.display = 'none';
    }

    showCancelModal() {
        if (!this.selectedAppointment) return;

        const date = new Date(this.selectedAppointment.appointment_date);
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

        document.getElementById('cancelModalText').innerHTML = `
            Вы уверены, что хотите отменить запись на
            <strong>${this.selectedAppointment.service_name}</strong><br>
            ${date.getDate()} ${monthNames[date.getMonth()]} в ${this.selectedAppointment.appointment_time}?
        `;

        document.getElementById('cancelModal').classList.add('active');
    }

    async cancelAppointment() {
        if (!this.selectedAppointment) return;

        const btn = document.getElementById('confirmCancelBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(
                `/api/appointments/${this.selectedAppointment.id}?phone=${encodeURIComponent(this.currentPhone)}`,
                {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'cancelled' })
                }
            );

            if (response.ok) {
                this.closeCancelModal();
                await this.searchBookings(); // Reload
                this.showNotification('Запись успешно отменена', 'success');
            } else {
                const data = await response.json();
                throw new Error(data.detail || 'Ошибка отмены');
            }
        } catch (error) {
            console.error('Cancel error:', error);
            this.showNotification('Ошибка: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Да, отменить';
        }
    }

    closeCancelModal() {
        document.getElementById('cancelModal').classList.remove('active');
        this.selectedAppointment = null;
    }

    showRescheduleModal() {
        if (!this.selectedAppointment) return;

        const modal = document.getElementById('rescheduleModal');
        const content = document.getElementById('rescheduleContent');

        content.innerHTML = `
            <div class="reschedule-current">
                <h4>Текущая запись:</h4>
                <p><strong>${this.selectedAppointment.service_name}</strong></p>
                <p>${this.selectedAppointment.appointment_date} в ${this.selectedAppointment.appointment_time}</p>
            </div>
            <div class="reschedule-form">
                <h4>Выберите новую дату и время:</h4>
                <div class="form-group">
                    <label>Дата</label>
                    <input type="date" id="newDate" min="${new Date().toISOString().split('T')[0]}">
                </div>
                <div class="time-slots-reschedule" id="rescheduleTimeSlots">
                    <p class="hint">Выберите дату для просмотра доступного времени</p>
                </div>
                <div class="reschedule-actions">
                    <button class="btn btn-outline" onclick="closeRescheduleModal()">Отмена</button>
                    <button class="btn btn-primary" id="confirmRescheduleBtn" disabled>
                        <i class="fas fa-check"></i> Перенести
                    </button>
                </div>
            </div>
        `;

        // Date change listener
        document.getElementById('newDate').addEventListener('change', (e) => {
            this.loadRescheduleTimeSlots(e.target.value);
        });

        modal.classList.add('active');
    }

    async loadRescheduleTimeSlots(dateStr) {
        const container = document.getElementById('rescheduleTimeSlots');
        container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i></div>';

        try {
            const response = await fetch(`/api/schedule/${dateStr}`);
            const data = await response.json();

            if (!data.is_working_day) {
                container.innerHTML = '<p class="error">Выходной день</p>';
                return;
            }

            const availableSlots = data.slots.filter(s => s.available);
            if (availableSlots.length === 0) {
                container.innerHTML = '<p class="error">Нет свободных слотов</p>';
                return;
            }

            container.innerHTML = `
                <div class="time-options">
                    ${availableSlots.map(s => `
                        <div class="time-option" data-time="${s.time}">${s.time}</div>
                    `).join('')}
                </div>
            `;

            // Time slot selection
            container.querySelectorAll('.time-option').forEach(opt => {
                opt.addEventListener('click', () => {
                    container.querySelectorAll('.time-option').forEach(o => o.classList.remove('selected'));
                    opt.classList.add('selected');
                    document.getElementById('confirmRescheduleBtn').disabled = false;
                });
            });

            // Confirm reschedule button
            document.getElementById('confirmRescheduleBtn').onclick = () => {
                const selectedTime = container.querySelector('.time-option.selected')?.dataset.time;
                if (selectedTime) {
                    this.rescheduleAppointment(dateStr, selectedTime);
                }
            };

        } catch (error) {
            console.error('Error loading time slots:', error);
            container.innerHTML = '<p class="error">Ошибка загрузки</p>';
        }
    }

    async rescheduleAppointment(newDate, newTime) {
        const btn = document.getElementById('confirmRescheduleBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(
                `/api/appointments/${this.selectedAppointment.id}?phone=${encodeURIComponent(this.currentPhone)}`,
                {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_date: newDate, new_time: newTime })
                }
            );

            if (response.ok) {
                closeRescheduleModal();
                await this.searchBookings();
                this.showNotification('Запись успешно перенесена', 'success');
            } else {
                const data = await response.json();
                throw new Error(data.detail || 'Ошибка переноса');
            }
        } catch (error) {
            console.error('Reschedule error:', error);
            this.showNotification('Ошибка: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Перенести';
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Global functions for modals
function closeRescheduleModal() {
    document.getElementById('rescheduleModal').classList.remove('active');
}

function closeCancelModal() {
    document.getElementById('cancelModal').classList.remove('active');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new MyBookingsPage();
});
