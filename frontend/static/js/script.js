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

document.addEventListener('DOMContentLoaded', function() {
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
                const headerHeight = header ? header.offsetHeight : 0;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
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
    if (expNumber) {
        const observerOptions = {
            threshold: 0.5
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
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
