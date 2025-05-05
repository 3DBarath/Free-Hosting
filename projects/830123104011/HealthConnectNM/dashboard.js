let heartRateData = [];
let intervalId;

function startVitalMonitoring() {
    intervalId = setInterval(() => {
        const newRate = Math.floor(Math.random() * 40 + 60);
        heartRateData.push(newRate);
        updateHeartRateDisplay(newRate);
        detectEmergency(newRate);
        updateTimeline();
    }, 3000);
}

function updateHeartRateDisplay(rate) {
    const heartRateElement = document.getElementById('heartRate');
    heartRateElement.textContent = rate;
    heartRateElement.style.color = rate > 100 ? 'var(--danger)' : 'var(--primary)';
}

function updateTimeline() {
    const timeline = document.getElementById('timeline');
    const event = document.createElement('div');
    event.className = 'timeline-event';
    event.innerHTML = `
        <small>${new Date().toLocaleTimeString()}</small>
        <p>Heart rate recorded: ${heartRateData.slice(-1)[0]} bpm</p>
    `;
    timeline.prepend(event);
}

function scheduleAppointment() {
    const date = prompt('Enter appointment date (YYYY-MM-DD):');
    if(date) {
        const appointments = storage.get('appointments') || [];
        appointments.push(date);
        storage.set('appointments', appointments);
        loadAppointments();
    }
}

function loadAppointments() {
    const appointments = storage.get('appointments') || [];
    const list = document.getElementById('appointments');
    list.innerHTML = appointments.map(date => `
        <div class="appointment-item">
            <span>📅 ${date}</span>
            <button onclick="cancelAppointment('${date}')">❌</button>
        </div>
    `).join('');
}

function cancelAppointment(date) {
    const appointments = storage.get('appointments').filter(d => d !== date);
    storage.set('appointments', appointments);
    loadAppointments();
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    startVitalMonitoring();
    loadAppointments();
});