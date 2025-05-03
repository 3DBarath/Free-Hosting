let currentFile = null;
let customProjectName = null;

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const zipInput = document.getElementById('zipInput');
const fileNameDisplay = document.getElementById('fileName');
const loader = document.querySelector('.loader');
const resultContainer = document.getElementById('resultContainer');
const nameDialog = document.getElementById('nameDialog');

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    zipInput.value = '';
    fileNameDisplay.textContent = 'No file selected';
    resultContainer.innerHTML = '';
});

// File Input Handling
zipInput.addEventListener('change', () => {
    fileNameDisplay.textContent = zipInput.files[0]?.name || 'No file selected';
});

// Drag & Drop Handling
uploadForm.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadForm.classList.add('dragover');
});

uploadForm.addEventListener('dragleave', () => {
    uploadForm.classList.remove('dragover');
});

uploadForm.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadForm.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        zipInput.files = e.dataTransfer.files;
        fileNameDisplay.textContent = e.dataTransfer.files[0].name;
    }
});

// Form Submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!zipInput.files.length) return alert('Please select a ZIP file');

    const originalName = zipInput.files[0].name.replace(/\.zip$/i, '');
    currentFile = zipInput.files[0];

    try {
        const isAvailable = await checkNameAvailability(originalName);
        
        if (isAvailable) {
            customProjectName = originalName;
            await performUpload();
        } else {
            showNameDialog(originalName);
        }
    } catch (err) {
        showNotification(`Error: ${err.message}`, '#ff6b6b');
    }
});

document.getElementById('projectName').addEventListener('input', function() {
document.getElementById('confirmBtn').disabled = true;
document.getElementById('nameStatus').textContent = '';
});

// Name Availability Check
async function checkNameAvailability(name) {
    const status = document.getElementById('nameStatus');
    status.textContent = 'Checking...';
    status.removeAttribute('data-status');

    try {
        const response = await fetch(`/api/check-name?name=${encodeURIComponent(name)}`);
        const data = await response.json();
        
        if(data.available) {
            status.textContent = '✓ Name available';
            status.setAttribute('data-status', 'success');
            return data.available;
        } else {
            status.textContent = '✗ Name already exists';
            status.setAttribute('data-status', 'error');
            return false;
        }
    } catch(err) {
        status.textContent = '⚠️ Check failed';
        status.setAttribute('data-status', 'error');
        return false;
    }
}

function toggleInstructions() {
    const modal = document.getElementById('instructionsModal');
    modal.style.display = modal.style.display === 'flex' ? 'none' : 'flex';
}

// Close modal when clicking outside
window.onclick = function(event) {
const modal = document.getElementById('instructionsModal');
if (event.target === modal) {
  modal.style.display = 'none';
}
}
function showNameDialog(defaultName) {
nameDialog.style.display = 'flex';
const nameInput = document.getElementById('projectName');
nameInput.value = defaultName;
document.getElementById('nameStatus').textContent = '';
document.getElementById('confirmBtn').disabled = true;

// Trigger input event to clear any previous state
nameInput.dispatchEvent(new Event('input'));
}

// Dialog Event Listeners
document.getElementById('checkBtn').addEventListener('click', async () => {
const nameInput = document.getElementById('projectName');
const name = nameInput.value.trim();
const status = document.getElementById('nameStatus');

if (!name) {
status.textContent = 'Please enter a name';
return;
}

status.textContent = 'Checking...';
const available = await checkNameAvailability(name);

if (available) {
status.textContent = '✓ Available!';
document.getElementById('confirmBtn').disabled = false;
customProjectName = name;
} else {
status.textContent = '✗ Already exists';
document.getElementById('confirmBtn').disabled = true;
}
});

document.getElementById('confirmBtn').addEventListener('click', async () => {
nameDialog.style.display = 'none';
if (customProjectName) await performUpload();
});

document.getElementById('cancelBtn').addEventListener('click', () => {
nameDialog.style.display = 'none';
currentFile = null;
customProjectName = null;
});

// Upload Handling
async function performUpload() {
    if (!currentFile || !customProjectName) return;

    loader.style.display = 'grid';
    const submitButton = uploadForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    try {
        const formData = new FormData();
        formData.append('zipfile', currentFile);
        formData.append('projectName', customProjectName);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        resultContainer.innerHTML = `
            <div class="result-card">
                <h2>🚀 Deployment Successful!</h2>
                <div class="links-container">
                    <a href="${data.viewUrl}" target="_blank" class="result-link">
                        🌍 Live Preview
                    </a>
                </div>
            </div>`;

        // Reset form
        zipInput.value = '';
        fileNameDisplay.textContent = 'No file selected';
        currentFile = null;
        customProjectName = null;

    } catch (err) {
        showNotification(`Upload failed: ${err.message}`, '#ff6b6b');
    } finally {
        loader.style.display = 'none';
        submitButton.disabled = false;
    }
}

// UI Helpers
function showNotification(message, color) {
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.bottom = '20px';
    notification.style.right = '20px';
    notification.style.padding = '1rem 2rem';
    notification.style.background = color;
    notification.style.color = 'var(--navy)';
    notification.style.borderRadius = '6px';
    notification.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => notification.remove(), 3000);
}

// View Toggles
document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    });
});