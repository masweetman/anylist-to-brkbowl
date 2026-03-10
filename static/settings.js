// DOM Elements
const settingsForm = document.getElementById('settingsForm');
const settingsMessage = document.getElementById('settingsMessage');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const listNameInput = document.getElementById('listName');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    attachEventListeners();
});

// Attach event listeners
function attachEventListeners() {
    settingsForm.addEventListener('submit', handleSaveSettings);
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
