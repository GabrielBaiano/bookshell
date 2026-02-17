import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".bookshell"
DB_PATH = DB_DIR / "bookshell.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Configuration table (root folder ID, local path, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Books table (synchronized metadata)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            drive_id TEXT NOT NULL,
            category TEXT,
            local_path TEXT,
            progress INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_config(key, value):
    """Saves or updates a configuration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_config(key):
    """Retrieves a configuration by name."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_book(title, drive_id, category=None, local_path=None, progress=0):
    """Registers a new book in the local database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO books (title, drive_id, category, local_path, progress)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, drive_id, category, local_path, progress))
    conn.commit()
    conn.close()

def list_cached_books():
    """Returns the list of locally saved books (works offline)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT title, category, drive_id, progress FROM books ORDER BY title ASC')
    books = cursor.fetchall()
    conn.close()
    return books

    return books

def delete_book_by_name(title):
    """Removes a book from the database by its title."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books WHERE title = ?', (title,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Initialising database...")
    init_db()
    print(f"Database created at: {DB_PATH}")
