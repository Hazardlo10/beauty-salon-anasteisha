/**
 * Anasteisha Beauty Salon Website
 * JavaScript - Animations & Interactivity
 */

// ==================== MAINTENANCE MODE ====================
// Чтобы включить режим технических работ, установите значение true
// Чтобы выключить - установите false
const MAINTENANCE_MODE = false;

// Время окончания работ (опционально) - формат: 'YYYY-MM-DD HH:MM'
const MAINTENANCE_END_TIME = null; // Пример: '2026-02-03 10:00'

// ==================== MAIN CODE ====================

// Отключаем автоматическое восстановление позиции скролла браузером
if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
}

document.addEventListener('DOMContentLoaded', function() {
    // Принудительный скролл в начало при загрузке (если нет якоря в URL)
    if (!window.location.hash) {
        window.scrollTo(0, 0);
    }

    // Check maintenance mode
    const maintenanceOverlay = document.getElementById('maintenanceMode');

    if (MAINTENANCE_MODE && maintenanceOverlay) {
        // Show maintenance mode
        maintenanceOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Update end time if specified
        if (MAINTENANCE_END_TIME) {
            const timeElement = maintenanceOverlay.querySelector('.maintenance-time span');
            if (timeElement) {
                const endDate = new Date(MAINTENANCE_END_TIME);
                const options = {
                    day: 'numeric',
                    month: 'long',
                    hour: '2-digit',
                    minute: '2-digit'
                };
                timeElement.textContent = 'Ожидаемое время завершения: ' +
                    endDate.toLocaleDateString('ru-RU', options);
            }
        }

        // Don't initialize the rest of the site
        return;
    } else if (maintenanceOverlay) {
        // Hide maintenance mode
        maintenanceOverlay.style.display = 'none';
    }
    // Initialize AOS (Animate on Scroll)
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 50,
            delay: 100
        });
    }

    // Preloader
    const preloader = document.getElementById('preloader');
    if (preloader) {
        window.addEventListener('load', function() {
            // Скролл в начало после загрузки (борьба с кешированием позиции браузером)
            if (!window.location.hash) {
                setTimeout(function() { window.scrollTo(0, 0); }, 0);
            }
            setTimeout(function() {
                preloader.classList.add('hidden');
            }, 500);
        });
        // Fallback: hide after 3 seconds
        setTimeout(function() {
            preloader.classList.add('hidden');
        }, 3000);
    }

    // Header scroll effect
    const header = document.getElementById('header');
    let lastScroll = 0;

    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        lastScroll = currentScroll;
    });

    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mainNav = document.getElementById('mainNav');

    if (mobileMenuToggle && mainNav) {
        mobileMenuToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            mainNav.classList.toggle('active');
            document.body.style.overflow = mainNav.classList.contains('active') ? 'hidden' : '';
        });

        // Close menu when clicking on a link
        const navLinks = mainNav.querySelectorAll('a');
        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                mobileMenuToggle.classList.remove('active');
                mainNav.classList.remove('active');
                document.body.style.overflow = '';
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!mainNav.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
                mobileMenuToggle.classList.remove('active');
                mainNav.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                // Add extra offset (20px) for better visibility
                const headerHeight = header ? header.offsetHeight + 20 : 120;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });

                // Close mobile menu if open
                const nav = document.querySelector('.nav');
                const menuToggle = document.querySelector('.mobile-menu-toggle');
                if (nav && nav.classList.contains('active')) {
                    nav.classList.remove('active');
                    if (menuToggle) menuToggle.classList.remove('active');
                }
            }
        });
    });

    // Scroll to top button
    const scrollToTopBtn = document.getElementById('scrollToTop');

    if (scrollToTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 500) {
                scrollToTopBtn.classList.add('visible');
            } else {
                scrollToTopBtn.classList.remove('visible');
            }
        });

        scrollToTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Form submission
    const bookingForm = document.getElementById('bookingForm');
    const successModal = document.getElementById('successModal');

    if (bookingForm) {
        bookingForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Get form data
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());

            // Simple validation
            if (!data.name || !data.phone || !data.service) {
                alert('Пожалуйста, заполните все обязательные поля');
                return;
            }

            // Phone validation
            const phoneRegex = /^[\d\s\+\-\(\)]{10,}$/;
            if (!phoneRegex.test(data.phone)) {
                alert('Пожалуйста, введите корректный номер телефона');
                return;
            }

            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            submitBtn.disabled = true;

            // Send to API
            fetch('/api/booking', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(result) {
                // Reset form
                bookingForm.reset();

                // Reset button
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;

                // Show success modal
                if (successModal) {
                    successModal.classList.add('active');
                } else {
                    alert('Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в ближайшее время.');
                }

                console.log('Booking sent:', result);
            })
            .catch(function(error) {
                // Reset button
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;

                alert('Произошла ошибка. Попробуйте позже или позвоните нам.');
                console.error('Error:', error);
            });
        });
    }

    // Phone input formatting
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');

            if (value.length > 0) {
                if (value[0] === '8') {
                    value = '7' + value.slice(1);
                }
                if (value[0] !== '7') {
                    value = '7' + value;
                }

                let formatted = '+7';
                if (value.length > 1) {
                    formatted += ' (' + value.slice(1, 4);
                }
                if (value.length > 4) {
                    formatted += ') ' + value.slice(4, 7);
                }
                if (value.length > 7) {
                    formatted += '-' + value.slice(7, 9);
                }
                if (value.length > 9) {
                    formatted += '-' + value.slice(9, 11);
                }

                e.target.value = formatted;
            }
        });
    }

    // Service cards hover animation enhancement
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });

    // Parallax effect for hero section
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const heroContent = hero.querySelector('.hero-content');
            if (heroContent && scrolled < window.innerHeight) {
                heroContent.style.transform = 'translateY(' + (scrolled * 0.3) + 'px)';
                heroContent.style.opacity = 1 - (scrolled / window.innerHeight);
            }
        });
    }

    // Animated counter for experience years
    const expNumber = document.querySelector('.exp-number');
    if (expNumber && !expNumber.dataset.animated) {
        const observerOptions = {
            threshold: 0.5
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting && !expNumber.dataset.animated) {
                    expNumber.dataset.animated = 'true';
                    animateCounter(expNumber, 0, 5, 1500);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        observer.observe(expNumber);
    }

    function animateCounter(element, start, end, duration) {
        const range = end - start;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(start + range * easeProgress);

            element.textContent = current + '+';

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                // Гарантируем конечное значение
                element.textContent = end + '+';
            }
        }

        requestAnimationFrame(update);
    }

    // Active navigation link highlighting
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav a');

    function highlightNavLink() {
        const scrollPos = window.pageYOffset + 200;

        sections.forEach(function(section) {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {
                navLinks.forEach(function(link) {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === '#' + sectionId) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightNavLink);

    // Ripple effect on buttons
    document.querySelectorAll('.btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ripple = document.createElement('span');
            ripple.style.cssText = 'position: absolute; background: rgba(255,255,255,0.5); border-radius: 50%; transform: scale(0); animation: ripple 0.6s linear; pointer-events: none;';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.width = ripple.style.height = Math.max(rect.width, rect.height) + 'px';
            ripple.style.marginLeft = ripple.style.marginTop = -Math.max(rect.width, rect.height) / 2 + 'px';

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(function() {
                ripple.remove();
            }, 600);
        });
    });

    // Add ripple animation keyframes
    const style = document.createElement('style');
    style.textContent = '@keyframes ripple { to { transform: scale(4); opacity: 0; } }';
    document.head.appendChild(style);

    console.log('Anasteisha Beauty Salon - Website Loaded Successfully');
});

// Close modal function (global)
function closeModal() {
    const modal = document.getElementById('successModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Close modal on background click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        closeModal();
        closeReviewModal();
        closeProblemModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeModal();
        closeReviewModal();
        closeProblemModal();
    }
});

// ==================== REVIEW MODAL ====================
var currentRating = 0;

function openReviewModal() {
    var modal = document.getElementById('reviewModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeReviewModal() {
    var modal = document.getElementById('reviewModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Star rating
document.addEventListener('DOMContentLoaded', function() {
    var stars = document.querySelectorAll('#starRating .star');
    stars.forEach(function(star) {
        star.addEventListener('click', function() {
            currentRating = parseInt(this.getAttribute('data-rating'));
            document.getElementById('reviewRating').value = currentRating;
            updateStars(currentRating);
        });
        star.addEventListener('mouseenter', function() {
            var rating = parseInt(this.getAttribute('data-rating'));
            updateStars(rating);
        });
    });

    var starRating = document.getElementById('starRating');
    if (starRating) {
        starRating.addEventListener('mouseleave', function() {
            updateStars(currentRating);
        });
    }

    // Review form submit
    var reviewForm = document.getElementById('reviewForm');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();

            if (currentRating === 0) {
                alert('Пожалуйста, поставьте оценку');
                return;
            }

            var formData = new FormData(this);
            var data = Object.fromEntries(formData.entries());
            data.rating = currentRating;

            var submitBtn = this.querySelector('button[type="submit"]');
            var originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            submitBtn.disabled = true;

            fetch('/api/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(function(response) { return response.json(); })
            .then(function(result) {
                // Отправляем цель в Яндекс.Метрику
                if (typeof ym !== 'undefined' && window.YM_COUNTER_ID) {
                    ym(window.YM_COUNTER_ID, 'reachGoal', 'review_submitted', { rating: currentRating });
                }
                reviewForm.reset();
                currentRating = 0;
                updateStars(0);
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                closeReviewModal();
                alert('Спасибо за ваш отзыв!');
            })
            .catch(function(error) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                alert('Произошла ошибка. Попробуйте позже.');
                console.error('Error:', error);
            });
        });
    }

    // Problem form submit
    var problemForm = document.getElementById('problemForm');
    if (problemForm) {
        problemForm.addEventListener('submit', function(e) {
            e.preventDefault();

            var formData = new FormData(this);
            var data = Object.fromEntries(formData.entries());
            data.page_url = window.location.href;

            var submitBtn = this.querySelector('button[type="submit"]');
            var originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            submitBtn.disabled = true;

            fetch('/api/problem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(function(response) { return response.json(); })
            .then(function(result) {
                problemForm.reset();
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                closeProblemModal();
                alert('Сообщение отправлено! Спасибо за обратную связь.');
            })
            .catch(function(error) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                alert('Произошла ошибка. Попробуйте позже.');
                console.error('Error:', error);
            });
        });
    }
});

function updateStars(rating) {
    var stars = document.querySelectorAll('#starRating .star');
    stars.forEach(function(star, index) {
        var icon = star.querySelector('i');
        if (index < rating) {
            star.classList.add('active');
            icon.classList.remove('far');
            icon.classList.add('fas');
        } else {
            star.classList.remove('active');
            icon.classList.remove('fas');
            icon.classList.add('far');
        }
    });
}

// ==================== PROBLEM MODAL ====================
function openProblemModal() {
    var modal = document.getElementById('problemModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        document.getElementById('problemPageUrl').value = window.location.href;
    }
}

function closeProblemModal() {
    var modal = document.getElementById('problemModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Scroll to booking function (global)
function scrollToBooking() {
    const bookingSection = document.getElementById('booking');
    if (bookingSection) {
        const header = document.getElementById('header');
        const headerHeight = header ? header.offsetHeight : 0;
        const targetPosition = bookingSection.getBoundingClientRect().top + window.pageYOffset - headerHeight;

        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
}

// ==================== THEME TOGGLE ====================
(function() {
    // Check for saved theme preference or system preference
    function getPreferredTheme() {
        var savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            return savedTheme;
        }
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    // Apply theme
    function applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }

    // Apply theme immediately to prevent flash
    applyTheme(getPreferredTheme());

    // Setup toggle button after DOM loads
    document.addEventListener('DOMContentLoaded', function() {
        var themeToggle = document.getElementById('themeToggle');

        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                var currentTheme = document.documentElement.getAttribute('data-theme');
                var newTheme = currentTheme === 'dark' ? 'light' : 'dark';

                applyTheme(newTheme);
                localStorage.setItem('theme', newTheme);
            });
        }

        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
                if (!localStorage.getItem('theme')) {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    });
})();

// ==================== WELCOME MODAL (New Visitors) ====================
function openWelcomeModal() {
    var modal = document.getElementById('welcomeModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeWelcomeModal() {
    var modal = document.getElementById('welcomeModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
    // Mark that user has seen the welcome modal
    localStorage.setItem('welcomeShown', 'true');
    localStorage.setItem('welcomeShownDate', new Date().toISOString());
}

// Show welcome modal for new visitors
document.addEventListener('DOMContentLoaded', function() {
    var welcomeShown = localStorage.getItem('welcomeShown');
    var welcomeShownDate = localStorage.getItem('welcomeShownDate');

    // Check if we should show the modal
    var shouldShow = false;

    if (!welcomeShown) {
        // Never shown before - show it
        shouldShow = true;
    } else if (welcomeShownDate) {
        // Check if 30 days have passed since last shown
        var lastShown = new Date(welcomeShownDate);
        var now = new Date();
        var daysPassed = (now - lastShown) / (1000 * 60 * 60 * 24);
        if (daysPassed > 30) {
            shouldShow = true;
        }
    }

    if (shouldShow) {
        // Show modal after a delay (let the page load first)
        setTimeout(function() {
            // Don't show if preloader is still visible
            var preloader = document.getElementById('preloader');
            if (preloader && !preloader.classList.contains('hidden')) {
                // Wait for preloader to hide
                setTimeout(function() {
                    openWelcomeModal();
                }, 1500);
            } else {
                openWelcomeModal();
            }
        }, 2000);
    }
});

// ========== CONSULTATION MODAL ==========
let selectedConsultationService = null;

async function loadConsultationServices() {
    const container = document.getElementById('consultationServices');
    if (!container) return;

    try {
        const response = await fetch('/api/services');
        let services = [];

        if (response.ok) {
            services = await response.json();
        } else {
            // Fallback
            services = [
                { id: 1, name: 'Атравматическая чистка лица' },
                { id: 2, name: 'Лифтинг-омоложение лица' },
                { id: 3, name: 'Липосомальное обновление кожи' },
                { id: 4, name: 'Ферментотерапия лица' },
                { id: 5, name: 'Безынъекционный ботокс лица' },
                { id: 6, name: 'Атравматическая чистка спины' },
                { id: 7, name: 'Лифтинг шеи и декольте' },
                { id: 8, name: 'Обновление лица и декольте' },
                { id: 9, name: 'Ботокс лица и шеи' },
            ];
        }

        container.innerHTML = services.map(s => `
            <button class="consultation-service-btn" data-service-id="${s.id}" data-service-name="${s.name}" onclick="selectConsultationService(this)">
                <i class="fas fa-spa"></i>
                <span>${s.name}</span>
                <i class="fas fa-check check-icon"></i>
            </button>
        `).join('');

    } catch (error) {
        console.error('Error loading services:', error);
    }
}

function selectConsultationService(btn) {
    // Remove selection from all buttons
    document.querySelectorAll('.consultation-service-btn').forEach(b => b.classList.remove('selected'));

    // Select this button
    btn.classList.add('selected');

    // Save selected service
    selectedConsultationService = {
        id: btn.dataset.serviceId,
        name: btn.dataset.serviceName
    };

    // Show form
    const form = document.getElementById('consultationForm');
    const serviceNameEl = document.getElementById('selectedServiceName');

    if (form && serviceNameEl) {
        serviceNameEl.textContent = selectedConsultationService.name;
        form.style.display = 'block';
    }
}

function openConsultationModal() {
    const modal = document.getElementById('consultationModal');
    if (modal) {
        loadConsultationServices();
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeConsultationModal() {
    const modal = document.getElementById('consultationModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';

        // Reset state
        selectedConsultationService = null;
        const form = document.getElementById('consultationForm');
        if (form) form.style.display = 'none';

        const phoneInput = document.getElementById('consultationPhone');
        if (phoneInput) phoneInput.value = '';

        document.querySelectorAll('.consultation-service-btn').forEach(b => b.classList.remove('selected'));
    }
}

async function submitConsultation() {
    if (!selectedConsultationService) {
        alert('Пожалуйста, выберите услугу');
        return;
    }

    const phoneInput = document.getElementById('consultationPhone');
    const phone = phoneInput ? phoneInput.value.trim() : '';

    if (!phone || phone.length < 10) {
        alert('Пожалуйста, введите номер телефона');
        if (phoneInput) phoneInput.focus();
        return;
    }

    try {
        const response = await fetch('/api/consultation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                service_name: selectedConsultationService.name,
                service_id: selectedConsultationService.id,
                phone: phone
            })
        });

        if (response.ok) {
            closeConsultationModal();
            alert('Спасибо! Мы свяжемся с вами в ближайшее время.');
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.detail || 'Попробуйте позже'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка. Попробуйте позже или позвоните нам.');
    }
}

// Close modal on backdrop click
document.addEventListener('click', function(e) {
    const modal = document.getElementById('consultationModal');
    if (modal && e.target === modal) {
        closeConsultationModal();
    }
});

// Close modal on Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeConsultationModal();
        closeSupportModal();
    }
});

// ==================== REVIEWS LOADING ====================
async function loadReviews() {
    const container = document.getElementById('reviewsContainer');
    if (!container) return;

    // Проверяем, есть ли статические отзывы
    const staticReviews = container.querySelector('.reviews-static');

    try {
        const response = await fetch('/api/reviews');
        if (!response.ok) throw new Error('Failed to load reviews');

        let reviews = await response.json();

        // Сортируем: отзывы с текстом первыми
        reviews = reviews.sort((a, b) => {
            const aHasText = a.review_text && a.review_text.trim().length > 0;
            const bHasText = b.review_text && b.review_text.trim().length > 0;
            if (aHasText && !bHasText) return -1;
            if (!aHasText && bHasText) return 1;
            return 0; // Сохраняем исходный порядок для одинаковых
        });

        // Если API вернул отзывы, добавляем их к статическим
        if (reviews.length > 0) {
            const dynamicHtml = reviews.map(review => `
                <div class="review-card">
                    <div class="review-header">
                        <div class="review-avatar">
                            <i class="fas fa-user"></i>
                        </div>
                        <div class="review-meta">
                            <span class="review-name">${escapeHtml(review.name)}</span>
                            <span class="review-date">${formatReviewDate(review.created_at)}</span>
                        </div>
                        <div class="review-rating">
                            ${generateStars(review.rating)}
                        </div>
                    </div>
                    <p class="review-text">${escapeHtml(review.review_text)}</p>
                </div>
            `).join('');

            if (staticReviews) {
                // Добавляем динамические отзывы в начало статических
                staticReviews.insertAdjacentHTML('afterbegin', dynamicHtml);
            } else {
                container.innerHTML = `<div class="reviews-grid">${dynamicHtml}</div>`;
            }
        }
        // Если отзывов нет, статические останутся

    } catch (error) {
        console.error('Error loading reviews:', error);
        // При ошибке статические отзывы останутся
    }
}

function generateStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<i class="fas fa-star"></i>';
        } else {
            stars += '<i class="far fa-star"></i>';
        }
    }
    return stars;
}

function formatReviewDate(dateStr) {
    const date = new Date(dateStr);
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                   'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load reviews on page load
document.addEventListener('DOMContentLoaded', function() {
    loadReviews();
});

// ==================== SUPPORT MODAL ====================
function openSupportModal() {
    const modal = document.getElementById('supportModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeSupportModal() {
    const modal = document.getElementById('supportModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        // Reset form
        const form = document.getElementById('supportForm');
        if (form) form.reset();
    }
}

// Support form submit
document.addEventListener('DOMContentLoaded', function() {
    const supportForm = document.getElementById('supportForm');
    if (supportForm) {
        supportForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = {
                name: formData.get('name') || 'Аноним',
                email: formData.get('email') || '',
                message: formData.get('message'),
                page_url: window.location.href
            };

            if (!data.message || data.message.trim().length < 5) {
                alert('Пожалуйста, опишите вашу проблему подробнее');
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/api/support', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    closeSupportModal();
                    alert('Сообщение отправлено! Мы разберёмся с проблемой.');
                } else {
                    const error = await response.json();
                    alert('Ошибка: ' + (error.detail || 'Попробуйте позже'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Произошла ошибка. Попробуйте позже.');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }
});

// Close support modal on backdrop click
document.addEventListener('click', function(e) {
    const modal = document.getElementById('supportModal');
    if (modal && e.target === modal) {
        closeSupportModal();
    }
});

// Phone formatting for consultation
document.addEventListener('DOMContentLoaded', function() {
    const phoneInput = document.getElementById('consultationPhone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
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
        });
    }
});

// ==================== SERVICE INFO MODAL ====================
const serviceInfoData = {
    'chistka-lica': {
        title: 'Атравматическая чистка лица',
        system: 'FlaxPeelFace',
        price: '2 500 ₽',
        duration: '60 мин',
        description: 'Деликатная процедура глубокого очищения кожи без механического воздействия. Использует современные энзимные и кислотные составы для растворения загрязнений.',
        suitable: 'Подходит для чувствительной, куперозной кожи, при акне и розацеа.',
        steps: [
            'Демакияж и очищение кожи',
            'Нанесение энзимной маски для размягчения',
            'Ультразвуковая чистка',
            'Кислотный пилинг (по типу кожи)',
            'Успокаивающая маска',
            'Нанесение финального крема с SPF'
        ],
        results: [
            'Глубокое очищение пор',
            'Выравнивание тона кожи',
            'Уменьшение воспалений',
            'Здоровое сияние кожи',
            'Подготовка к дальнейшему уходу'
        ]
    },
    'lifting-lica': {
        title: 'Лифтинг-омоложение лица',
        system: 'FlaxLift',
        price: '2 800 ₽',
        duration: '90 мин',
        description: 'Интенсивная антивозрастная процедура с использованием пептидных комплексов и активных сывороток. Стимулирует выработку коллагена и эластина.',
        suitable: 'Рекомендуется при возрастных изменениях, потере упругости, нечётком овале лица.',
        steps: [
            'Глубокое очищение',
            'Пептидная сыворотка',
            'Миофасциальный массаж',
            'Лифтинг-маска с коллагеном',
            'Моделирование овала лица',
            'Закрепляющий уход'
        ],
        results: [
            'Подтяжка овала лица',
            'Разглаживание морщин',
            'Повышение упругости кожи',
            'Улучшение цвета лица',
            'Видимый эффект омоложения'
        ]
    },
    'liposomalnoe': {
        title: 'Липосомальное обновление кожи',
        system: 'FlaxNewSkin',
        price: '2 800 ₽',
        duration: '90 мин',
        description: 'Инновационная доставка активных веществ в глубокие слои кожи с помощью липосом. Обеспечивает интенсивное увлажнение, питание и регенерацию клеток.',
        suitable: 'Идеально для обезвоженной, тусклой кожи с признаками усталости.',
        steps: [
            'Мягкое очищение',
            'Пилинг с AHA-кислотами',
            'Липосомальная сыворотка',
            'Ионофорез для глубокого проникновения',
            'Питательная маска',
            'Защитный крем'
        ],
        results: [
            'Глубокое увлажнение',
            'Восстановление барьерных функций',
            'Сияющий цвет лица',
            'Гладкая, бархатистая кожа',
            'Длительный эффект питания'
        ]
    },
    'fermentoterapiya': {
        title: 'Ферментотерапия лица',
        system: 'FlaxEnzyme',
        price: '2 800 ₽',
        duration: '75 мин',
        description: 'Мягкий энзимный пилинг на основе натуральных ферментов папайи и ананаса. Деликатно растворяет ороговевшие клетки, очищает поры, выравнивает тон кожи.',
        suitable: 'Подходит для всех типов кожи, включая чувствительную.',
        steps: [
            'Подготовка кожи',
            'Нанесение ферментного состава',
            'Время экспозиции под плёнкой',
            'Нейтрализация',
            'Увлажняющая маска',
            'Защитный уход'
        ],
        results: [
            'Мягкое обновление кожи',
            'Ровный тон без пигментации',
            'Сужение пор',
            'Свежий, отдохнувший вид',
            'Подготовка к другим процедурам'
        ]
    },
    'botoks-lica': {
        title: 'Безынъекционный ботокс лица',
        system: 'FlaxSpicule',
        price: '2 800 ₽',
        duration: '90 мин',
        description: 'Процедура с аргирелином и пептидным комплексом. Расслабляет мимические мышцы, разглаживает морщины лба и межбровья. Безопасная альтернатива инъекциям.',
        suitable: 'Для тех, кто хочет эффект ботокса без уколов. При мимических морщинах.',
        steps: [
            'Очищение и подготовка',
            'Нанесение пептидной сыворотки с аргирелином',
            'Микротоковая терапия',
            'Маска с ботокс-эффектом',
            'Массаж по массажным линиям',
            'Закрепляющий уход'
        ],
        results: [
            'Расслабление мимических мышц',
            'Разглаживание морщин на лбу',
            'Уменьшение межбровной складки',
            'Отдохнувший вид лица',
            'Накопительный эффект'
        ]
    },
    'chistka-spiny': {
        title: 'Атравматическая чистка спины',
        system: 'FlaxPeelFace',
        price: '4 500 ₽',
        duration: '90 мин',
        description: 'Профессиональное очищение кожи спины от высыпаний, комедонов и воспалений. Включает распаривание, энзимный пилинг, бережную экстракцию и успокаивающую маску.',
        suitable: 'При акне на спине, жирной коже с комедонами, перед пляжным сезоном.',
        steps: [
            'Очищение зоны спины',
            'Распаривание и размягчение',
            'Энзимный пилинг',
            'Ультразвуковая чистка',
            'Точечная обработка воспалений',
            'Успокаивающая маска',
            'Защитный уход'
        ],
        results: [
            'Чистая кожа без высыпаний',
            'Сужение расширенных пор',
            'Уменьшение жирности',
            'Ровный тон кожи',
            'Профилактика новых воспалений'
        ]
    },
    'lifting-shei': {
        title: 'Лифтинг шеи и декольте',
        system: 'FlaxLift',
        price: '3 500 ₽',
        duration: '75 мин',
        description: 'Специальный уход за деликатной зоной шеи и декольте. Устраняет дряблость, пигментацию, мелкие морщины. Коллагеновые маски и моделирующий массаж.',
        suitable: 'При возрастных изменениях в зоне шеи, "кольцах Венеры", пигментации.',
        steps: [
            'Деликатное очищение',
            'Мягкий пилинг',
            'Лифтинг-сыворотка',
            'Массаж шеи и декольте',
            'Коллагеновая маска',
            'Укрепляющий уход'
        ],
        results: [
            'Подтянутая кожа шеи',
            'Уменьшение "колец Венеры"',
            'Ровный тон декольте',
            'Упругость и эластичность',
            'Молодой вид зоны'
        ]
    },
    'obnovlenie-kompleks': {
        title: 'Обновление лица и декольте',
        system: 'FlaxNewSkin',
        price: '3 500 ₽',
        duration: '120 мин',
        description: 'Комплексная anti-age программа для лица и зоны декольте. Включает пилинг, сыворотки с гиалуроновой кислотой, коллагеновую маску и моделирующий массаж.',
        suitable: 'Для комплексного омоложения, при возрастных изменениях обеих зон.',
        steps: [
            'Очищение лица и декольте',
            'Мультикислотный пилинг',
            'Гиалуроновая сыворотка',
            'Массаж лица и декольте',
            'Коллагеновые маски на обе зоны',
            'LED-терапия',
            'Финальный уход'
        ],
        results: [
            'Комплексное омоложение',
            'Единый тон лица и декольте',
            'Интенсивное увлажнение',
            'Подтянутая кожа',
            'Длительный эффект'
        ]
    },
    'botoks-kompleks': {
        title: 'Ботокс лица и шеи',
        system: 'FlaxSpicule',
        price: '3 800 ₽',
        duration: '105 мин',
        description: 'Расширенная безынъекционная процедура ботокс-эффекта для лица и шеи. Пептидные комплексы расслабляют мимику, лифтинг-маска подтягивает контуры обеих зон.',
        suitable: 'Максимальный эффект омоложения без инъекций для лица и шеи.',
        steps: [
            'Двойное очищение',
            'Пептидная сыворотка с аргирелином',
            'Микротоки на лицо и шею',
            'Ботокс-маска на обе зоны',
            'Скульптурный массаж',
            'RF-лифтинг',
            'Закрепляющий уход'
        ],
        results: [
            'Расслабление мимики лица и шеи',
            'Разглаживание морщин',
            'Чёткий овал и контур шеи',
            'Омоложение на 5-7 лет',
            'Накопительный долгосрочный эффект'
        ]
    }
};

function showServiceInfo(serviceId) {
    const service = serviceInfoData[serviceId];
    if (!service) return;

    const modal = document.getElementById('serviceInfoModal');
    const content = document.getElementById('serviceInfoContent');

    content.innerHTML = `
        <div class="service-info-header">
            <h3>${service.title}</h3>
            <p class="service-info-system">${service.system}</p>
        </div>

        <div class="service-info-meta">
            <span><i class="fas fa-ruble-sign"></i> ${service.price}</span>
            <span><i class="far fa-clock"></i> ${service.duration}</span>
        </div>

        <div class="service-info-section">
            <p class="service-info-desc">${service.description}</p>
            <p class="service-info-suitable"><i class="fas fa-check-circle"></i> ${service.suitable}</p>
        </div>

        <div class="service-info-section">
            <h4><i class="fas fa-list-ol"></i> Этапы процедуры</h4>
            <ol class="service-info-steps">
                ${service.steps.map(step => `<li>${step}</li>`).join('')}
            </ol>
        </div>

        <div class="service-info-section">
            <h4><i class="fas fa-star"></i> Результат</h4>
            <ul class="service-info-results">
                ${service.results.map(result => `<li><i class="fas fa-check"></i> ${result}</li>`).join('')}
            </ul>
        </div>

        <a href="#booking" class="btn btn-primary service-info-book" onclick="closeServiceInfoModal()">
            <i class="fas fa-calendar-check"></i> Записаться на процедуру
        </a>
    `;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeServiceInfoModal() {
    const modal = document.getElementById('serviceInfoModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// Close on backdrop click
document.addEventListener('click', function(e) {
    const modal = document.getElementById('serviceInfoModal');
    if (modal && e.target === modal) {
        closeServiceInfoModal();
    }
});

// Close on Escape (add to existing handler)
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeServiceInfoModal();
    }
});

// ==================== FAQ ACCORDION ====================
document.addEventListener('DOMContentLoaded', function() {
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(function(item) {
        const question = item.querySelector('.faq-question');

        question.addEventListener('click', function() {
            // Close other items
            faqItems.forEach(function(otherItem) {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });

            // Toggle current item
            item.classList.toggle('active');
        });
    });
});

// ========== BOOKING MODAL ==========
function openBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.classList.add('active');
        document.body.classList.add('booking-modal-open');
    }
}

function closeBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.classList.remove('booking-modal-open');

        // Сброс виджета для новой записи (отложенно, после анимации закрытия)
        setTimeout(function() {
            if (window.bookingWidgetInstance) {
                window.bookingWidgetInstance.currentStep = 1;
                window.bookingWidgetInstance.selectedService = null;
                window.bookingWidgetInstance.selectedDate = null;
                window.bookingWidgetInstance.selectedTime = null;
                window.bookingWidgetInstance.renderWidget();
            }
        }, 300);
    }
}

// Закрытие по Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeBookingModal();
    }
});

// Перехват кликов по ссылке "Запись" в навигации
document.addEventListener('DOMContentLoaded', function() {
    // Находим ссылку на запись в навигации
    const bookingLinks = document.querySelectorAll('a[href="#booking"]');
    bookingLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            openBookingModal();
        });
    });
});
