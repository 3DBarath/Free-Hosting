const hospitals = [
    { 
        name: "City General Hospital", 
        lat: 40.7128, 
        lng: -74.0060,
        type: "hospital",
        services: ["Emergency", "Surgery", "ICU"],
        contact: "555-1234"
    },
    {
        name: "Community Health Clinic",
        lat: 40.7282,
        lng: -74.0776,
        type: "clinic",
        services: ["Primary Care", "Vaccinations"],
        contact: "555-5678"
    }
];

let map;

function initMap() {
    // Initialize map with original styling
    map = L.map('map').setView([40.7128, -74.0060], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add custom hospital markers
    hospitals.forEach(hospital => {
        const marker = L.marker([hospital.lat, hospital.lng], {
            icon: L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41]
            })
        }).addTo(map)
        .bindPopup(`
            <div class="map-popup">
                <h4>🏥 ${hospital.name}</h4>
                <p>Services: ${hospital.services.join(', ')}</p>
                <p>📞 ${hospital.contact}</p>
            </div>
        `);
    });

    // Original filter functionality
    document.querySelectorAll('.filter-option').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-option').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterServices(this.dataset.type);
        });
    });
}

function filterServices(type) {
    const results = type === 'all' 
        ? hospitals 
        : hospitals.filter(h => h.type === type);
    
    const resultsHTML = results.map(hospital => `
        <div class="clinic-card">
            <h3>${hospital.type === 'hospital' ? '🏥' : '🩺'} ${hospital.name}</h3>
            <p>📌 ${hospital.lat.toFixed(4)}, ${hospital.lng.toFixed(4)}</p>
            <p>📞 ${hospital.contact}</p>
            <div class="services">
                ${hospital.services.map(s => `<span class="service-tag">${s}</span>`).join('')}
            </div>
        </div>
    `).join('');
    
    document.getElementById('serviceResults').innerHTML = resultsHTML;
}

document.addEventListener('DOMContentLoaded', initMap);