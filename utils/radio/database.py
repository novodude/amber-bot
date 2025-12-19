import aiosqlite
import os

DB_PATH = "data/radio.db"

async def init_db():
    """Initialize the database with tables"""
    os.makedirs("data", exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Playlists table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                is_public BOOLEAN DEFAULT 0,
                source_url TEXT,
                source_type TEXT,
                last_synced TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Songs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                artist TEXT,
                file_path TEXT NOT NULL,
                duration INTEGER,
                file_hash TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)
        
        # User settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                default_volume REAL DEFAULT 0.5,
                auto_mix BOOLEAN DEFAULT 0
            )
        """)
        
        await db.commit()
