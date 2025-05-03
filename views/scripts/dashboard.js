document.addEventListener('DOMContentLoaded', () => {
    // Add event listeners
    document.querySelector('.toggle-header').addEventListener('click', toggleActivityLogs);
    document.addEventListener('click', handleButtonClicks);
    
    // Initialize app
    loadActivityLogs();
    initialize();
});


let logsVisible = false;
let baseUrl = '';

// Event handler for all button clicks
function handleButtonClicks(e) {
    if (e.target.classList.contains('delete-btn')) {
        handleDeleteClick(e);
    }
    if (e.target.classList.contains('share-btn')) {
        handleShareClick(e);
    }
}

function toggleActivityLogs() {
    const activityList = document.getElementById('activity-list');
    const arrow = document.getElementById('toggleArrow');
    
    logsVisible = !logsVisible;
    activityList.classList.toggle('collapsed');
    arrow.style.transform = logsVisible ? 'rotate(0deg)' : 'rotate(180deg)';
}
// Updated JavaScript with modern UI feedback
async function deleteProject(projectId, projectFolder, listItem) {
    if (!projectId || !projectFolder) {
        alert('Invalid project data');
        return;
    }
    if (!confirm('Are you sure you want to delete this project?')) return;
    
    try {
        const response = await fetch(`/api/delete-project/${projectId}`, {
            method: 'DELETE',
        });

        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || 'Failed to delete project');
        }
        
        listItem.style.opacity = '0';
        setTimeout(() => listItem.remove(), 300);
        showNotification('Project deleted successfully', 'var(--teal)');
        // Optional: Remove folder from server
        await fetch(`/api/cleanup/${projectFolder}`, { method: 'POST' });
        
    } catch (err) {
        showNotification(err.message, '#ff6b6b');
    }
}

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
async function fetchRegno() {
const response = await fetch('/get_regno');
const data = await response.json();
return data.regno;
}
// Update the delete handler in your dashboard script
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('delete-btn')) {
        const listItem = e.target.closest('.upload-item');
        const projectId = e.target.dataset.id;
        const projectFolder = e.target.dataset.folder;
        
        if (!projectId || !projectFolder) {
            alert('Invalid project data');
            return;
        }
        
        deleteProject(projectId, projectFolder, listItem);
    }
});

// Add this before the fetchRegno() call
async function fetchBaseUrl() {
    const response = await fetch('/get_base_url');
    const data = await response.json();
    baseUrl = data.base_url;
}

// Add this error logging function
function handleClipboardError(err) {
    console.error('Clipboard error:', err);
    const tempInput = document.createElement('input');
    const fullUrl = window.location.href; // Fallback URL
    tempInput.value = fullUrl;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    alert('URL copied to clipboard!');
}

// Modified share handler with better feedback
// Update the share button event listener
// Update the share button handler
document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.share-btn');
    if (btn) {
        try {
            // Get the actual view project URL from the anchor tag
            const viewLink = btn.closest('.upload-actions').querySelector('a').href;
            
            // Visual feedback
            const originalText = btn.innerHTML;
            btn.innerHTML = '⏳ Copying...';
            btn.style.pointerEvents = 'none';

            // Try modern clipboard API first
            await navigator.clipboard.writeText(viewLink);
            
            // Success feedback
            btn.innerHTML = '✅ Copied!';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.pointerEvents = 'auto';
            }, 2000);

        } catch (err) {
            // Fallback for browsers that block clipboard access
            const viewLink = btn.closest('.upload-actions').querySelector('a').href;
            const tempInput = document.createElement('input');
            tempInput.value = viewLink;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            // Show success feedback even for fallback
            btn.innerHTML = '✅ Copied!';
            setTimeout(() => {
                btn.innerHTML = '🔗 Share';
                btn.style.pointerEvents = 'auto';
            }, 2000);
        }
    }
});

// Update the initialization flow
async function initialize() {
try {
    await fetchBaseUrl();
    const regno = await fetchRegno();
    // Rest of your dashboard loading code
} catch (error) {
    console.error('Initialization error:', error);
    alert('Failed to initialize page');
}
}



fetchRegno().then(regno => {
fetch('/api/dashboard')
    .then(response => {
        if (!response.ok) throw new Error('Failed to load uploads');
        return response.json();
    })
    .then(data => {
        const list = document.getElementById('uploads-list');
        if (data.uploads && data.uploads.length > 0) {
            data.uploads.forEach((upload, index) => {
                const li = document.createElement('li');
                li.className = 'upload-item';
                li.style.animationDelay = `${index * 0.1}s`;
                // Use the regno here after it's fetched
                li.innerHTML = `
                    <div class="upload-info">
                        <strong>📄 ${upload.project_folder}</strong>
                        <div class="upload-actions">
                            <a href="/projects/${regno}/${upload.project_folder}" target="_blank">
                                  View Project
                            </a>
                            <button class="share-btn" 
                                    data-path="${upload.project_folder}">
                                🔗 Share
                            </button>
                            <button class="delete-btn" 
                                    data-id="${upload.id}"
                                    data-folder="${upload.project_folder}">
                                🗑 Delete
                            </button>
                        </div>
                    </div>
                    <div class="upload-time">
                        <i class="far fa-clock"></i>
                        ${new Date(upload.upload_time).toLocaleString()}
                    </div>`;
                list.appendChild(li);
            });
        } else {
            list.innerHTML = '<li>No uploads found.</li>';
        }
    })
    .catch(error => {
        console.error('Error loading uploads:', error);
        alert('Failed to load uploads');
    });
}).catch(error => {
console.error('Error fetching regno:', error);
alert('Failed to fetch regno');
});
// Add these functions to dashboard.html's script
async function loadActivityLogs() {
    const activityList = document.getElementById('activity-list');
    const adminBadge = document.getElementById('adminBadge');
    
    try {
        // Show loading state
        activityList.innerHTML = '<div class="activity-item">Loading activities...</div>';

        const response = await fetch('/api/activity-logs');
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Validate response structure
        if (!data || !Array.isArray(data.logs)) {
            throw new Error('Invalid activity data format');
        }

        // Clear existing content
        activityList.innerHTML = '';

        // Process registration numbers for admin view
        const regnos = data.logs.map(log => log.regno).filter(Boolean);
        const isAdminView = new Set(regnos).size > 1;
        adminBadge.style.display = isAdminView ? 'inline-block' : 'none';

        if (data.logs.length > 0) {
            data.logs.forEach(log => {
                const logItem = document.createElement('div');
                logItem.className = `activity-item ${isAdminView ? 'admin-log' : ''}`;
                
                logItem.innerHTML = `
                    <div class="activity-time">
                        ${new Date(log.created_at).toLocaleString()}
                        ${log.ip_address ? `• ${log.ip_address}` : ''}
                    </div>
                    <div class="activity-action">
                        ${isAdminView ? `<span class="user-regno">${log.regno}</span>` : ''}
                        <div class="activity-icon">
                            ${getActionIcon(log.action_type)}
                        </div>
                        ${log.description || formatDefaultAction(log.action_type)}
                    </div>
                `;
                activityList.appendChild(logItem);
            });
        } else {
            activityList.innerHTML = '<div class="activity-item">No activity records found</div>';
        }

        // Ensure section is expanded after load
        if (!logsVisible) toggleActivityLogs();

    } catch (error) {
        console.error('Activity log error:', error);
        activityList.innerHTML = `
            <div class="activity-item error">
                ⚠️ Failed to load activities: ${error.message}
            </div>
        `;
        showNotification(`Activity Error: ${error.message}`, '#ff6b6b');
        
        // Collapse section on error
        if (logsVisible) toggleActivityLogs();
    }
}

// Enhanced helper functions
function getActionIcon(actionType) {
    const iconMap = {
        upload: '📤',
        delete: '🗑️',
        login: '🔑',
        logout: '🚪',
        view: '👁️',
        register: '📝',
        download: '📥',
        update: '🔄'
    };
    return iconMap[actionType] || '📄';
}

function formatDefaultAction(actionType) {
    const actionMap = {
        upload: 'Uploaded project files',
        delete: 'Deleted a project',
        login: 'Logged into system',
        logout: 'Logged out from system',
        view: 'Viewed project',
        register: 'Registered new account',
        download: 'Downloaded project',
        update: 'Updated project'
    };
    return actionMap[actionType] || `Performed ${actionType} action`;
}