import aiosqlite
import os

DB_PATH = "data/radio.db"

async def init_radio_db():
    """Initialize the radio database (streaming-only, no file downloads)."""
    os.makedirs("data", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                artist TEXT,
                stream_url TEXT NOT NULL,
                duration INTEGER,
                file_hash TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                default_volume REAL DEFAULT 0.5,
                auto_mix BOOLEAN DEFAULT 0
            )
        """)

        # ── Migrations for existing databases ─────────────────────────────────
        migrations = [
            "ALTER TABLE songs ADD COLUMN stream_url TEXT",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        await db.commit()
