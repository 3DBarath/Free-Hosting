document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.toggle-header').addEventListener('click', toggleActivityLogs);
    document.addEventListener('click', handleButtonClicks);
    loadActivityLogs();
    initialize();
});

let logsVisible = false;
let baseUrl = '';

function handleButtonClicks(e) {
    if (e.target.classList.contains('delete-btn')) {
        handleDeleteClick(e);
    }
    if (e.target.classList.contains('share-btn')) {
        handleShareClick(e);
    }
    if (e.target.classList.contains('pin-btn')) {
        handlePinClick(e);
    }
}

async function handlePinClick(e) {
    const btn = e.target;
    const projectId = btn.dataset.id;
    const isPinned = btn.dataset.pinned === 'true';

    try {
        const response = await fetch(`/api/toggle-pin/${projectId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pinned: !isPinned })
        });

        if (!response.ok) throw new Error('Failed to toggle pin');

        const data = await response.json();
        btn.dataset.pinned = data.newState;
        // btn.textContent = data.newState ? '📌Unpin' : '📌 Pin';

        const listItem = btn.closest('.upload-item');
        listItem.classList.toggle('pinned-project', data.newState);
        
        sortProjects();
        showNotification(data.newState ? 'Project pinned!' : 'Project unpinned', 'var(--teal)');

    } catch (err) {
        showNotification(err.message, '#ff6b6b');
    }
}
function sortProjects() {
    const list = document.getElementById('uploads-list');
    const items = Array.from(list.children);
    
    items.sort((a, b) => {
        const aPinned = a.querySelector('.pin-btn').dataset.pinned === 'true';
        const bPinned = b.querySelector('.pin-btn').dataset.pinned === 'true';
        return bPinned - aPinned;
    });

    items.forEach(item => list.appendChild(item));
}
function toggleActivityLogs() {
    const activityList = document.getElementById('activity-list');
    const arrow = document.getElementById('toggleArrow');
    
    logsVisible = !logsVisible;
    activityList.classList.toggle('collapsed');
    arrow.style.transform = logsVisible ? 'rotate(0deg)' : 'rotate(180deg)';
}

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

async function fetchBaseUrl() {
    const response = await fetch('/get_base_url');
    const data = await response.json();
    baseUrl = data.base_url;
}

function handleClipboardError(err) {
    console.error('Clipboard error:', err);
    const tempInput = document.createElement('input');
    const fullUrl = window.location.href;
    tempInput.value = fullUrl;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    alert('URL copied to clipboard!');
}

document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.share-btn');
    if (btn) {
        try {
            const viewLink = btn.closest('.upload-actions').querySelector('a').href;
            
            const originalText = btn.innerHTML;
            btn.innerHTML = '⏳ Copying...';
            btn.style.pointerEvents = 'none';

            await navigator.clipboard.writeText(viewLink);
            
            btn.innerHTML = '✅ Copied!';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.pointerEvents = 'auto';
            }, 2000);

        } catch (err) {
            const viewLink = btn.closest('.upload-actions').querySelector('a').href;
            const tempInput = document.createElement('input');
            tempInput.value = viewLink;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            btn.innerHTML = '✅ Copied!';
            setTimeout(() => {
                btn.innerHTML = '🔗 Share';
                btn.style.pointerEvents = 'auto';
            }, 2000);
        }
    }
});


async function initialize() {
try {
    await fetchBaseUrl();
    const regno = await fetchRegno();
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
                li.className = `upload-item ${upload.is_pinned ? 'pinned-project' : ''}`;
                li.style.animationDelay = `${index * 0.1}s`;
                li.innerHTML = `
                    <div class="project-header">
                        <strong>✨${upload.project_folder}✨</strong>
                        <button class="pin-btn" 
                            data-id="${upload.id}"
                            data-pinned="${upload.is_pinned}">
                            ${upload.is_pinned ? '📌' : '📌'}
                        </button>
                    </div>
                    <div class="project-details">
                        <div class="upload-time">
                            <i class="far fa-clock"></i>
                            ${new Date(upload.upload_time).toLocaleString()}
                        </div>
                        <div class="upload-actions">
                            <a href="/projects/${regno}/${upload.project_folder}" target="_blank" class="view-btn">
                                <i class="fas fa-eye"></i> View
                            </a>
                            <button class="share-btn" data-path="${upload.project_folder}">
                                <i class="fas fa-share"></i> Share
                            </button>
                            <button class="delete-btn" 
                                data-id="${upload.id}"
                                data-folder="${upload.project_folder}">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>

                    </div>
                `;
                list.appendChild(li);
            });
            sortProjects();
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

async function loadActivityLogs() {
    const activityList = document.getElementById('activity-list');
    const adminBadge = document.getElementById('adminBadge');
    
    try {
        activityList.innerHTML = '<div class="activity-item">Loading activities...</div>';

        const response = await fetch('/api/activity-logs');
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data || !Array.isArray(data.logs)) {
            throw new Error('Invalid activity data format');
        }

        activityList.innerHTML = '';

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

        if (!logsVisible) toggleActivityLogs();

    } catch (error) {
        console.error('Activity log error:', error);
        activityList.innerHTML = `
            <div class="activity-item error">
                ⚠️ Failed to load activities: ${error.message}
            </div>
        `;
        showNotification(`Activity Error: ${error.message}`, '#ff6b6b');
        
        if (logsVisible) toggleActivityLogs();
    }
}


function getActionIcon(actionType) {
    const iconMap = {
        upload: '📤',
        delete: '🗑️',
        login: '🔑',
        logout: '🚪',
        view: '👁️',
        register: '📝',
        download: '📥',
        update: '🔄',
        pin: '📌',
        unpin: '📍'
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
        update: 'Updated project',
        pin: 'Pinned a project',
        unpin: 'Unpinned a project'
    };
    return actionMap[actionType] || `Performed ${actionType} action`;
}