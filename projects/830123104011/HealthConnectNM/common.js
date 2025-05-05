// Navigation handling
document.addEventListener('DOMContentLoaded', () => {
    // Set active navigation
    const currentPage = location.pathname.split('/').pop();
    document.querySelectorAll('.main-nav a').forEach(link => {
        if(link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });

    // Initialize toast container
    const toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    document.body.appendChild(toastContainer);
});

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    document.getElementById('toast-container').appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Local storage wrapper
const storage = {
    get: (key) => JSON.parse(localStorage.getItem(key)),
    set: (key, value) => localStorage.setItem(key, JSON.stringify(value)),
    clear: () => localStorage.clear()
};

// Emergency detection
let emergencyTimeout;
function detectEmergency(heartRate) {
    if(heartRate > 120 || heartRate < 50) {
        showToast('Abnormal heart rate detected!', 'emergency');
        document.documentElement.style.setProperty('--primary', '#ef4444');
        clearTimeout(emergencyTimeout);
        emergencyTimeout = setTimeout(() => {
            document.documentElement.style.setProperty('--primary', '#2563eb');
        }, 5000);
    }
}