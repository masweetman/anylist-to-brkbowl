// DOM Elements
const settingsForm = document.getElementById('settingsForm');
const settingsMessage = document.getElementById('settingsMessage');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const listNameInput = document.getElementById('listName');

const cookiesForm = document.getElementById('cookiesForm');
const cookiesMessage = document.getElementById('cookiesMessage');
const cookiesTextarea = document.getElementById('cookiesTextarea');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadCookies();
    attachEventListeners();
});

// Attach event listeners
function attachEventListeners() {
    settingsForm.addEventListener('submit', handleSaveSettings);
    cookiesForm.addEventListener('submit', handleSaveCookies);
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

// Load cookies from server
async function loadCookies() {
    try {
        const response = await fetch('/api/cookies');
        const data = await response.json();
        
        if (data.cookies) {
            // Parse and pretty-print the JSON
            try {
                const parsed = JSON.parse(data.cookies);
                cookiesTextarea.value = JSON.stringify(parsed, null, 2);
            } catch {
                cookiesTextarea.value = data.cookies;
            }
        }
    } catch (error) {
        console.error('Error loading cookies:', error);
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

// Handle save cookies
async function handleSaveCookies(e) {
    e.preventDefault();

    const cookiesText = cookiesTextarea.value.trim();

    if (!cookiesText) {
        showMessage('error', 'Please enter cookie data', cookiesMessage);
        return;
    }

    // Validate JSON
    try {
        JSON.parse(cookiesText);
    } catch (err) {
        showMessage('error', `Invalid JSON: ${err.message}`, cookiesMessage);
        return;
    }

    try {
        const response = await fetch('/api/cookies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cookies: cookiesText,
            }),
        });

        if (response.ok) {
            showMessage('success', 'Cookies saved successfully!', cookiesMessage);
            setTimeout(() => {
                cookiesMessage.innerHTML = '';
            }, 3000);
        } else {
            const error = await response.json();
            showMessage('error', error.error || 'Failed to save cookies', cookiesMessage);
        }
    } catch (error) {
        console.error('Error saving cookies:', error);
        showMessage('error', 'Error saving cookies', cookiesMessage);
    }
}

// Show message
function showMessage(type, text, targetElement = settingsMessage) {
    targetElement.className = `message ${type}`;
    targetElement.textContent = text;
}
