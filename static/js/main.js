// Form Validation
function validateForm(formElement) {
    const form = formElement || document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    });
}

// Date Range Picker
function initializeDatePicker() {
    const checkIn = document.getElementById('check_in');
    const checkOut = document.getElementById('check_out');
    
    if (checkIn && checkOut) {
        const today = new Date().toISOString().split('T')[0];
        checkIn.min = today;
        
        checkIn.addEventListener('change', function() {
            checkOut.min = this.value;
            if (checkOut.value && checkOut.value < this.value) {
                checkOut.value = this.value;
            }
            updateTotalPrice();
        });

        checkOut.addEventListener('change', function() {
            updateTotalPrice();
        });
    }
}

// Price Calculator
function updateTotalPrice() {
    const checkIn = document.getElementById('check_in');
    const checkOut = document.getElementById('check_out');
    const roomSelect = document.getElementById('room_type');
    const totalPriceElement = document.getElementById('total-price');
    
    if (checkIn && checkOut && roomSelect && totalPriceElement) {
        const startDate = new Date(checkIn.value);
        const endDate = new Date(checkOut.value);
        
        if (startDate && endDate && endDate > startDate) {
            const days = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
            const selectedOption = roomSelect.options[roomSelect.selectedIndex];
            const price = parseFloat(selectedOption.dataset.price);
            const totalPrice = days * price;
            totalPriceElement.textContent = `$${totalPrice.toFixed(2)}`;

            // Update hidden total price input if it exists
            const hiddenTotalPrice = document.getElementById('total_price');
            if (hiddenTotalPrice) {
                hiddenTotalPrice.value = totalPrice.toFixed(2);
            }
        }
    }
}

// Payment Form Validation
function initializePaymentForm() {
    const cardNumber = document.getElementById('card_number');
    const cvv = document.getElementById('cvv');
    const cardName = document.getElementById('card_name');

    if (cardNumber) {
        cardNumber.addEventListener('input', function(e) {
            this.value = this.value.replace(/\D/g, '').substring(0, 16);
            // Add spaces every 4 digits
            this.value = this.value.replace(/(\d{4})(?=\d)/g, '$1 ');
        });
    }

    if (cvv) {
        cvv.addEventListener('input', function(e) {
            this.value = this.value.replace(/\D/g, '').substring(0, 4);
        });
    }

    if (cardName) {
        cardName.addEventListener('input', function(e) {
            this.value = this.value.replace(/[0-9]/g, '');
        });
    }
}

// Search Form
function initializeSearchForm() {
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        const cityInput = searchForm.querySelector('#city');
        const roomTypeSelect = searchForm.querySelector('#room_type');
        
        // Add debounce to city search
        let timeout = null;
        cityInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                // Here you can add AJAX call to fetch city suggestions
                console.log('Searching for:', this.value);
            }, 500);
        });
    }
}

// Image Gallery
function initializeGallery() {
    const carousel = document.getElementById('hotelCarousel');
    if (carousel) {
        // Initialize Bootstrap carousel
        new bootstrap.Carousel(carousel, {
            interval: 3000,
            wrap: true
        });
    }
}

// Flash Messages
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(flash => {
        setTimeout(() => {
            const closeButton = flash.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });
}

// Profile Page Tabs
function initializeProfileTabs() {
    const tabElements = document.querySelectorAll('a[data-bs-toggle="tab"]');
    tabElements.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            // Save the currently active tab to localStorage
            localStorage.setItem('activeProfileTab', event.target.id);
        });
    });

    // Restore active tab on page load
    const activeTab = localStorage.getItem('activeProfileTab');
    if (activeTab) {
        const tab = document.getElementById(activeTab);
        if (tab) {
            new bootstrap.Tab(tab).show();
        }
    }
}

// Password Validation
function initializePasswordValidation() {
    const passwordForm = document.querySelector('form[action*="change_password"]');
    if (passwordForm) {
        const newPassword = passwordForm.querySelector('#new_password');
        const confirmPassword = passwordForm.querySelector('#confirm_password');

        confirmPassword.addEventListener('input', function() {
            if (this.value !== newPassword.value) {
                this.setCustomValidity("Passwords don't match");
            } else {
                this.setCustomValidity('');
            }
        });

        newPassword.addEventListener('input', function() {
            if (confirmPassword.value) {
                if (this.value !== confirmPassword.value) {
                    confirmPassword.setCustomValidity("Passwords don't match");
                } else {
                    confirmPassword.setCustomValidity('');
                }
            }
        });
    }
}

// Initialize all components
document.addEventListener('DOMContentLoaded', function() {
    validateForm();
    initializeDatePicker();
    initializePaymentForm();
    initializeSearchForm();
    initializeGallery();
    initializeFlashMessages();
    initializeProfileTabs();
    initializePasswordValidation();

    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add animation class to elements
    document.querySelectorAll('.animate-on-scroll').forEach(element => {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        });
        observer.observe(element);
    });
});

// Handle booking cancellation
function handleBookingCancellation(bookingId) {
    if (confirm('Are you sure you want to cancel this booking?')) {
        fetch(`/cancel-booking/${bookingId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.message || 'Failed to cancel booking');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while canceling the booking');
        });
    }
}

// Handle room availability check
function checkRoomAvailability(roomId, checkIn, checkOut) {
    fetch(`/check-availability/${roomId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
            check_in: checkIn,
            check_out: checkOut
        })
    })
    .then(response => response.json())
    .then(data => {
        const availabilityElement = document.getElementById(`room-${roomId}-availability`);
        if (availabilityElement) {
            availabilityElement.textContent = data.available ? 'Available' : 'Not Available';
            availabilityElement.className = data.available ? 'text-success' : 'text-danger';
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Export functions for use in other scripts
window.hotelApp = {
    validateForm,
    updateTotalPrice,
    handleBookingCancellation,
    checkRoomAvailability
};
