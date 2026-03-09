// DOM Elements
const importBtn = document.getElementById('importBtn');
const addToCartBtn = document.getElementById('addToCartBtn');
const exportCsvBtn = document.getElementById('exportCsvBtn');
const importCsvBtn = document.getElementById('importCsvBtn');
const importModal = document.getElementById('importModal');
const csvImportModal = document.getElementById('csvImportModal');
const closeBtn = document.querySelector('.close');
const importForm = document.getElementById('importForm');
const csvImportForm = document.getElementById('csvImportForm');
const newItemInput = document.getElementById('newItemInput');
const addItemBtn = document.getElementById('addItemBtn');
const itemsList = document.getElementById('itemsList');
const emptyState = document.getElementById('emptyState');
const importMessage = document.getElementById('importMessage');
const csvImportMessage = document.getElementById('csvImportMessage');
const skipBtn = document.getElementById('skipBtn');
const skipBar = document.getElementById('skipBar');
const skipBarText = document.getElementById('skipBarText');

let items = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadItems();
    attachEventListeners();
});

// Event Listeners
function attachEventListeners() {
    importBtn.addEventListener('click', openImportModal);
    addToCartBtn.addEventListener('click', handleAddAllToCart);
    exportCsvBtn.addEventListener('click', handleExportCsv);
    importCsvBtn.addEventListener('click', openCsvImportModal);
    closeBtn.addEventListener('click', closeImportModal);
    
    // Multiple close buttons for both modals
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === importModal) closeImportModal();
        if (e.target === csvImportModal) closeCsvImportModal();
    });
    importForm.addEventListener('submit', handleImport);
    csvImportForm.addEventListener('submit', handleCsvImport);
    addItemBtn.addEventListener('click', addItem);
    newItemInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addItem();
    });
}

// Load items from server
async function loadItems() {
    try {
        const response = await fetch('/api/items');
        items = await response.json();
        renderItems();
    } catch (error) {
        console.error('Error loading items:', error);
    }
}

// Render items to the DOM
function renderItems() {
    itemsList.innerHTML = '';

    if (items.length === 0) {
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
    }

    items.forEach((item) => {
        const itemEl = createItemElement(item);
        itemsList.appendChild(itemEl);
    });
}

// Create item element
function createItemElement(item) {
    const div = document.createElement('div');
    div.className = `item ${item.complete ? 'complete' : ''}`;
    div.dataset.id = item.id;

    const urlDisplay = item.url ? `<a href="${encodeURI(item.url)}" target="_blank">${item.url}</a>` : 'No URL';

    div.innerHTML = `
        <input 
            type="checkbox" 
            class="item-checkbox" 
            ${item.complete ? 'checked' : ''}
        >
        <div class="item-content">
            <div class="item-name">${escapeHtml(item.name)}</div>
            <div class="item-url">${urlDisplay}</div>
        </div>
        <div class="item-actions">
            <button class="btn-secondary edit-btn">Edit</button>
        </div>
    `;

    // Add event listeners
    const checkbox = div.querySelector('.item-checkbox');
    const editBtn = div.querySelector('.edit-btn');

    checkbox.addEventListener('change', () => toggleComplete(item.id, checkbox.checked));
    editBtn.addEventListener('click', () => enterEditMode(item.id, div));

    return div;
}

// Add new item
async function addItem() {
    const name = newItemInput.value.trim();

    if (!name) {
        alert('Please enter an item name');
        return;
    }

    try {
        const response = await fetch('/api/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url: '' }),
        });

        if (response.ok) {
            const newItem = await response.json();
            items.push(newItem);
            renderItems();
            newItemInput.value = '';
            newItemInput.focus();
        } else if (response.status === 409) {
            alert('This item already exists');
        } else {
            const error = await response.json();
            alert(error.error);
        }
    } catch (error) {
        console.error('Error adding item:', error);
        alert('Error adding item');
    }
}

// Toggle item complete status
async function toggleComplete(itemId, complete) {
    try {
        const response = await fetch(`/api/items/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ complete }),
        });

        if (response.ok) {
            const updated = await response.json();
            const itemIndex = items.findIndex((i) => i.id === itemId);
            if (itemIndex !== -1) {
                items[itemIndex] = updated;
                renderItems();
            }
        }
    } catch (error) {
        console.error('Error updating item:', error);
    }
}

// Delete item

// Enter edit mode
function enterEditMode(itemId, itemEl) {
    const item = items.find((i) => i.id === itemId);
    if (!item) return;

    const content = itemEl.querySelector('.item-content');
    content.innerHTML = `
        <div class="item-edit-mode">
            <input 
                type="text" 
                class="edit-name" 
                value="${escapeHtml(item.name)}" 
                placeholder="Item name"
            >
            <input 
                type="text" 
                class="edit-url" 
                value="${escapeHtml(item.url || '')}" 
                placeholder="Item URL (optional)"
            >
            <div class="edit-mode-actions">
                <button class="btn-save save-edit-btn">Save</button>
                <button class="btn-cancel cancel-edit-btn">Cancel</button>
            </div>
        </div>
    `;

    const saveBtn = content.querySelector('.save-edit-btn');
    const cancelBtn = content.querySelector('.cancel-edit-btn');
    const nameInput = content.querySelector('.edit-name');

    saveBtn.addEventListener('click', () => saveEdit(itemId));
    cancelBtn.addEventListener('click', () => renderItems());
    nameInput.focus();
}

// Save edit
async function saveEdit(itemId) {
    const item = items.find((i) => i.id === itemId);
    const itemEl = document.querySelector(`[data-id="${itemId}"]`);
    
    if (!itemEl) return;

    const nameInput = itemEl.querySelector('.edit-name');
    const urlInput = itemEl.querySelector('.edit-url');

    const newName = nameInput.value.trim();
    const newUrl = urlInput.value.trim();

    if (!newName) {
        alert('Item name cannot be empty');
        return;
    }

    try {
        const response = await fetch(`/api/items/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName, url: newUrl }),
        });

        if (response.ok) {
            const updated = await response.json();
            const itemIndex = items.findIndex((i) => i.id === itemId);
            if (itemIndex !== -1) {
                items[itemIndex] = updated;
                renderItems();
            }
        } else if (response.status === 409) {
            alert('An item with this name already exists');
        } else {
            const error = await response.json();
            alert(error.error);
        }
    } catch (error) {
        console.error('Error updating item:', error);
        alert('Error updating item');
    }
}

// Import Modal Functions
async function openImportModal() {
    importModal.classList.add('show');
    importMessage.innerHTML = '';
    importForm.reset();
    
    // Load saved settings
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        if (settings.anylist_email) {
            document.getElementById('email').value = settings.anylist_email;
        }
        if (settings.anylist_password) {
            document.getElementById('password').value = settings.anylist_password;
        }
        if (settings.anylist_list_name) {
            document.getElementById('listName').value = settings.anylist_list_name;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function closeImportModal() {
    importModal.classList.remove('show');
    importMessage.innerHTML = '';
}

// Handle import
async function handleImport(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const listName = document.getElementById('listName').value;

    importMessage.innerHTML = '';
    importBtn.disabled = true;

    try {
        const response = await fetch('/api/import-anylist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, list_name: listName }),
        });

        const data = await response.json();

        if (response.ok) {
            // Build detailed message with import stats
            let message = data.message;
            if (data.imported_count > 0 || data.updated_count > 0) {
                const details = [];
                if (data.imported_count > 0) {
                    details.push(`${data.imported_count} new item${data.imported_count !== 1 ? 's' : ''}`);
                }
                if (data.updated_count > 0) {
                    details.push(`${data.updated_count} existing item${data.updated_count !== 1 ? 's' : ''} updated`);
                }
                message = `${data.message}\n(${details.join(', ')})`;
            }
            
            showMessage('success', message);
            importForm.reset();
            setTimeout(() => {
                closeImportModal();
                loadItems();
            }, 1500);
        } else {
            showMessage('error', data.error || 'Import failed');
        }
    } catch (error) {
        console.error('Error importing:', error);
        showMessage('error', 'Error importing from AnyList');
    } finally {
        importBtn.disabled = false;
    }
}

// Show message in modal
function showMessage(type, text) {
    importMessage.className = `message ${type}`;
    importMessage.textContent = text;
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Handle add all to cart
async function handleAddAllToCart() {
    // Check if there are any incomplete items  
    const incompleteItems = items.filter(item => !item.complete);
    
    if (incompleteItems.length === 0) {
        alert('No incomplete items to add to cart');
        return;
    }
    
    // Confirm action
    const confirmed = confirm(`Add ${incompleteItems.length} item(s) to cart? This may take a few minutes.`);
    if (!confirmed) return;
    
    // Disable button during process
    const originalText = addToCartBtn.textContent;
    addToCartBtn.disabled = true;
    addToCartBtn.textContent = 'Adding to cart...';
    
    try {
        const response = await fetch('/api/add-to-cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cart_url: 'https://shop.heinzcatering.berkeleybowl.com/'
            }),
            timeout: 300000 // 5 minute timeout
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let message = `Added ${data.added.length} items to cart`;
            
            // Count items with captured URLs
            const urlsCaptured = data.added.filter(item => {
                return typeof item === 'object' && item.url && item.url.length > 0;
            }).length;
            
            if (urlsCaptured > 0) {
                message += `\n${urlsCaptured} items now have direct product URLs saved`;
            }
            
            if (data.failed && data.failed.length > 0) {
                message += `\nFailed: ${data.failed.length} items`;
            }
            alert(message);
            
            // Reload items to show updated URLs
            await loadItems();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        alert('Error adding items to cart. Please try again.');
    } finally {
        // Re-enable button
        addToCartBtn.disabled = false;
        addToCartBtn.textContent = originalText;
    }
}

// Export items to CSV
async function handleExportCsv() {
    try {
        const response = await fetch('/api/export-csv');
        if (response.ok) {
            // Create a blob from the response
            const blob = await response.blob();
            // Create a temporary URL for the blob
            const url = window.URL.createObjectURL(blob);
            // Create a temporary anchor element to trigger download
            const a = document.createElement('a');
            a.href = url;
            a.download = 'shopping_list.csv';
            document.body.appendChild(a);
            a.click();
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            alert('Shopping list exported successfully!');
        } else {
            alert('Error exporting CSV');
        }
    } catch (error) {
        console.error('Error exporting CSV:', error);
        alert('Error exporting shopping list. Please try again.');
    }
}

// Open CSV import modal
function openCsvImportModal() {
    csvImportModal.style.display = 'block';
}

function closeCsvImportModal() {
    csvImportModal.style.display = 'none';
    csvImportForm.reset();
    csvImportMessage.innerHTML = '';
}

// Handle CSV import
async function handleCsvImport(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        csvImportMessage.className = 'message error';
        csvImportMessage.textContent = 'Please select a file';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/import-csv', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            let message = `✅ Import complete!\n`;
            message += `• Imported: ${data.imported_count}\n`;
            message += `• Updated: ${data.updated_count}\n`;
            
            if (data.errors && data.errors.length > 0) {
                message += `• Errors: ${data.errors.length}`;
            }
            
            csvImportMessage.className = 'message success';
            csvImportMessage.textContent = message;
            
            // Reload items after a short delay
            setTimeout(() => {
                loadItems();
                closeCsvImportModal();
            }, 1500);
        } else {
            csvImportMessage.className = 'message error';
            csvImportMessage.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        console.error('Error importing CSV:', error);
        csvImportMessage.className = 'message error';
        csvImportMessage.textContent = 'Error importing CSV. Please try again.';
    }
}

