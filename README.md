# AnyList → Berkeley Bowl

A Flask web app for managing a shopping list and guiding you through adding items to your Berkeley Bowl online cart. Syncs completion status with AnyList.

## Features

- Import shopping lists from AnyList (syncs checkmarks both ways)
- Interactive cart assistant — opens Berkeley Bowl in a tab and walks you through each item one by one
- Add, edit, and manually check off items
- Import/export via CSV
- Persistent SQLite storage

---

## Deploying on Ubuntu Server

### 1. Install system dependencies

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx
```

### 2. Clone the repository

```bash
cd /srv
sudo git clone <your-repo-url> anylist-to-brkbowl
sudo chown -R $USER:$USER /srv/anylist-to-brkbowl
cd /srv/anylist-to-brkbowl
```

### 3. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install gunicorn
```

### 4. Configure environment variables

Create a `.env` file:

```bash
nano .env
```

Contents:

```
FLASK_ENV=production
```

### 5. Create a systemd service

```bash
sudo nano /etc/systemd/system/anylist-brkbowl.service
```

Paste:

```ini
[Unit]
Description=AnyList to Berkeley Bowl Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/anylist-to-brkbowl
ExecStart=/srv/anylist-to-brkbowl/.venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5001 \
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Set ownership and enable the service:

```bash
sudo chown -R www-data:www-data /srv/anylist-to-brkbowl
sudo systemctl daemon-reload
sudo systemctl enable anylist-brkbowl
sudo systemctl start anylist-brkbowl
```

Check it started successfully:

```bash
sudo systemctl status anylist-brkbowl
```

### 6. Configure Nginx as a reverse proxy

```bash
sudo nano /etc/nginx/sites-available/anylist-brkbowl
```

Paste (replace `your.domain.com` with your domain or server IP):

```nginx
server {
    listen 80;
    server_name your.domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/anylist-brkbowl /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

The app is now accessible at `http://your.domain.com`.

### 7. Enable HTTPS with Let's Encrypt (recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

Certbot updates your Nginx config automatically and sets up auto-renewal.

---

## How to Use

### Import from AnyList

1. Go to **Settings** and enter your AnyList email, password, and list name.
2. Click **Import from AnyList** on the main page. All items from that list are imported; previously complete items are reset to incomplete.

### Add items to your Berkeley Bowl cart

1. Click **Add all to cart**. A new tab opens with the shopping assistant.
2. For each incomplete item, Berkeley Bowl loads in the tab — either directly on the product page (if a URL is saved) or on a search results page.
3. Add the item to your cart, then click **✓ Added to Cart** to move to the next item.
4. Click **Skip** to leave an item for later without marking it complete.
5. Click **✕ Cancel** to end the session and close the tab.
6. When finished, each completed item is crossed off in AnyList automatically.

### Manage items manually

- **Add**: Type a name in the input field and press Enter or click **Add**.
- **Edit**: Click **Edit** on any item to change its name or URL.
- **Check/Uncheck**: Toggle the checkbox — syncs to AnyList if the item was imported from there.
- **Export/Import CSV**: Use the CSV buttons to back up or bulk-import items.

---

## Project Structure

```
anylist-to-brkbowl/
├── app.py              # Flask application and API routes
├── database.py         # SQLAlchemy models
├── requirements.txt    # Python dependencies
├── .env                # Environment variables
├── templates/
│   ├── index.html      # Shopping list page
│   ├── interact.html   # Interactive cart assistant
│   └── settings.html   # Settings page
└── static/
    ├── style.css
    ├── script.js       # Shopping list UI
    └── settings.js     # Settings UI
```

---

## Troubleshooting

**AnyList import fails** — Double-check your email and password in Settings. The list name must match exactly, or leave it blank to use the first list in your account.

**App won't start** — Check logs with `sudo journalctl -u anylist-brkbowl -n 50`.

**Berkeley Bowl blocks the iframe** — Some browsers or network configurations may prevent embedding. Check the browser console for errors.

**Reset the database** — Delete `instance/shopping_list.db` and restart the app. The schema is recreated automatically.
