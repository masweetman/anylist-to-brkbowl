# Shopping List Flask App

A Flask web application for managing shopping lists with the ability to import items from AnyList.

## Features

- ✅ Add, edit, and delete shopping items
- ✅ Mark items as complete/incomplete with checkboxes
- ✅ Add and edit URLs for each item
- ✅ Click URLs to open them in a new tab
- ✅ Import shopping lists from AnyList
- ✅ **Settings page** to save AnyList credentials and list name
- ✅ **Add all to cart** - Automatically add incomplete items to Amazon cart using Playwright
- ✅ Persistent storage with SQLite database
- ✅ Responsive and modern UI

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## How to Use

### Adding Items

1. Type the item name in the input field
2. Click "Add" or press Enter
3. Optionally add a URL by clicking the "Edit" button on the item

### Managing Items

- **Mark Complete**: Check the checkbox next to an item
- **Edit Item**: Click the "Edit" button to modify the name or URL
- **Delete Item**: Click the "Delete" button to remove an item
- **Open URL**: Click on the URL text to open it in a new tab

### Using Settings

1. Click the "Settings" button in the top right of the shopping list page
2. Enter your **AnyList email** and **password**
3. (Optional) Enter the **shopping list name** you want to import by default
4. Click "Save Settings"
5. Your settings are now saved and will be used when you import from AnyList

### Importing from AnyList

1. Click the "Import from AnyList" button
2. Your saved credentials and list name will be pre-filled automatically
3. Edit them if needed, or click "Import" to use the saved settings
4. Items from AnyList will be added to your shopping list (complete status reset to FALSE)
5. Existing items will have their complete status reset to FALSE

### Add Items to Shopping Cart

1. Click the "Add all to cart" button at the top right
2. Confirm the action when prompted
3. The app will use Playwright (browser automation) to:
   - **For items with URLs**: Navigate directly to the product URL and click the "Add to cart" button
   - **For items without URLs**: Navigate to the search page, search for the item by name, and wait for you to manually select the product (30 second timeout)
4. This process may take several minutes depending on how many items you have and whether you need to manually select products

## AnyList Library

This app uses the [pyanylist](https://github.com/ozonejunkieau/pyanylist) Python library to authenticate and import data from AnyList. pyanylist is an unofficial Python binding for the AnyList API, built with Rust and PyO3 for performance.

## Project Structure

```
anylist-to-brkbowl/
├── app.py              # Main Flask application
├── database.py         # Database models and setup
├── requirements.txt    # Python dependencies
├── .env                # Environment variables
├── templates/
│   ├── index.html      # Shopping list page
│   └── settings.html   # Settings page
└── static/
    ├── style.css       # Styling
    ├── script.js       # Shopping list functionality
    └── settings.js     # Settings page functionality
```

## Database Schema

### ShoppingItem Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Item name (unique) |
| complete | Boolean | Completion status |
| url | String | Optional URL for the item |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |
### Settings Table

| Column | Type | Description |
|--------|------|-----------|
| id | Integer | Primary key |
| anylist_email | String | Saved AnyList email |
| anylist_password | String | Saved AnyList password |
| anylist_list_name | String | Default AnyList list name to import |
| updated_at | DateTime | Last update timestamp |
## API Endpoints

### Shopping List
- `GET /` - Render the main shopping list page
- `GET /api/items` - Get all items
- `POST /api/items` - Create a new item
- `PUT /api/items/<id>` - Update an item
- `DELETE /api/items/<id>` - Delete an item
- `POST /api/import-anylist` - Import items from AnyList

### Settings
- `GET /settings` - Render the settings page
- `GET /api/settings` - Get user settings
- `POST /api/settings` - Save user settings

## Troubleshooting

### AnyList Import Fails

- Verify your email and password are correct
- Make sure your AnyList account is active
- Check that you have items in the list you're trying to import

### Database Errors

- Delete `shopping_list.db` to reset the database
- The database will be recreated automatically

## License

MIT
