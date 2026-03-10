// DOM Elements
const settingsForm = document.getElementById('settingsForm');
const settingsMessage = document.getElementById('settingsMessage');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const listNameInput = document.getElementById('listName');
const passwordForm = document.getElementById('passwordForm');
const passwordMessage = document.getElementById('passwordMessage');
const passwordStatus = document.getElementById('passwordStatus');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    attachEventListeners();
});

// Attach event listeners
function attachEventListeners() {
    settingsForm.addEventListener('submit', handleSaveSettings);
    passwordForm.addEventListener('submit', handleSetPassword);
}

// Load settings from server
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        if (settings.anylist_email) {
            emailInput.value = settings.anylist_email;
        }
        if (settings.anylist_password) {
            passwordInput.value = settings.anylist_password;
        }
        if (settings.anylist_list_name) {
            listNameInput.value = settings.anylist_list_name;
        }
        passwordStatus.textContent = settings.has_password
            ? '🔒 Password protection is enabled.'
            : '🔓 No password set — the app is publicly accessible.';
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Handle save settings
async function handleSaveSettings(e) {
    e.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const listName = listNameInput.value.trim();

    if (!email || !password) {
        showMessage('error', 'Email and password are required');
        return;
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                anylist_email: email,
                anylist_password: password,
                anylist_list_name: listName || '',
            }),
        });

        if (response.ok) {
            showMessage('success', 'Settings saved successfully!');
            setTimeout(() => {
                settingsMessage.innerHTML = '';
            }, 3000);
        } else {
            const error = await response.json();
            showMessage('error', error.error || 'Failed to save settings', settingsMessage);
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showMessage('error', 'Error saving settings', settingsMessage);
    }
}

// Show message
function showMessage(type, text, targetElement = settingsMessage) {
    targetElement.className = `message ${type}`;
    targetElement.textContent = text;
}

// Handle set/change/remove app password
async function handleSetPassword(e) {
    e.preventDefault();
    const newPassword = document.getElementById('appPassword').value;

    try {
        const response = await fetch('/api/settings/password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: newPassword }),
        });

        const data = await response.json();
        if (response.ok) {
            const msg = data.has_password ? 'Password set successfully.' : 'Password removed. App is now publicly accessible.';
            showMessage('success', msg, passwordMessage);
            passwordStatus.textContent = data.has_password
                ? '🔒 Password protection is enabled.'
                : '🔓 No password set — the app is publicly accessible.';
            document.getElementById('appPassword').value = '';
            setTimeout(() => { passwordMessage.innerHTML = ''; }, 3000);
        } else {
            showMessage('error', data.error || 'Failed to update password', passwordMessage);
        }
    } catch (error) {
        console.error('Error setting password:', error);
        showMessage('error', 'Error updating password', passwordMessage);
    }
}
