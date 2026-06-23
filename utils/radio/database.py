import aiosqlite
import discord
import os

DB_PATH = "data/radio.db"


# ── Init ───────────────────────────────────────────────────────────────────────

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
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                UNIQUE (playlist_id, stream_url)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                default_volume REAL DEFAULT 0.5,
                auto_mix BOOLEAN DEFAULT 0
            )
        """)

        migrations = [
            "ALTER TABLE songs ADD COLUMN stream_url TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_songs_playlist_stream ON songs (playlist_id, stream_url)",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        await db.commit()


# ── Favorites ──────────────────────────────────────────────────────────────────

async def create_fav_playlist(user: discord.User):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO playlists (name, owner_id, is_public)
            VALUES ("my liked songs", ?, 0)
        """, (user.id,))
        await db.commit()

async def get_fav_playlist_id(user: discord.User):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id FROM playlists
            WHERE owner_id = ? AND name = "my liked songs"
        """, (user.id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def add_song_to_favorites(user: discord.User, title: str, artist: str, stream_url: str, duration: int) -> bool:
    playlist_id = await get_fav_playlist_id(user)
    if not playlist_id:
        await create_fav_playlist(user)
        playlist_id = await get_fav_playlist_id(user)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO songs (playlist_id, title, artist, stream_url, duration)
            VALUES (?, ?, ?, ?, ?)
        """, (playlist_id, title, artist, stream_url, duration))
        await db.commit()
        return cursor.rowcount > 0

async def remove_song_from_favorites(user: discord.User, stream_url: str):
    playlist_id = await get_fav_playlist_id(user)
    if not playlist_id:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM songs WHERE playlist_id = ? AND stream_url = ?
        """, (playlist_id, stream_url))
        await db.commit()


# ── Playlists ──────────────────────────────────────────────────────────────────

async def get_accessible_playlists(user_id: int, limit: int = 25) -> list[tuple]:
    """Playlists owned by user or public, with song counts. Used for player dropdown."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.owner_id, COUNT(s.id) as cnt
            FROM playlists p
            LEFT JOIN songs s ON p.id = s.playlist_id
            WHERE p.owner_id = ? OR p.is_public = 1
            GROUP BY p.id HAVING cnt > 0 ORDER BY p.name LIMIT ?
        """, (user_id, limit))
        return await cursor.fetchall()

async def get_user_playlists(user_id: int, limit: int = 24) -> list[tuple]:
    """Playlists owned by user only. Used for add-to-playlist selects."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, name FROM playlists
            WHERE owner_id = ?
            ORDER BY name LIMIT ?
        """, (user_id, limit))
        return await cursor.fetchall()

async def get_playlist(playlist_id: int) -> tuple | None:
    """Returns (name, owner_id, is_public) or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name, owner_id, is_public FROM playlists WHERE id = ?", (playlist_id,)
        )
        return await cursor.fetchone()

async def get_playlist_for_sync(playlist_id: int) -> tuple | None:
    """Returns (name, owner_id, source_url, source_type) or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name, owner_id, source_url, source_type FROM playlists WHERE id = ?", (playlist_id,)
        )
        return await cursor.fetchone()

async def get_user_libraries(user_id: int) -> list[tuple]:
    """Returns user's own playlists with song counts, ordered by creation date."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.is_public, p.source_type, COUNT(s.id)
            FROM playlists p LEFT JOIN songs s ON p.id = s.playlist_id
            WHERE p.owner_id = ?
            GROUP BY p.id ORDER BY p.created_at DESC
        """, (user_id,))
        return await cursor.fetchall()

async def get_public_libraries() -> list[tuple]:
    """Returns all public playlists with song counts."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.owner_id, p.source_type, COUNT(s.id)
            FROM playlists p LEFT JOIN songs s ON p.id = s.playlist_id
            WHERE p.is_public = 1
            GROUP BY p.id HAVING COUNT(s.id) > 0 ORDER BY p.name
        """)
        return await cursor.fetchall()

async def playlist_name_exists(user_id: int, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM playlists WHERE owner_id = ? AND name = ?", (user_id, name)
        )
        return await cursor.fetchone() is not None

async def create_playlist(user_id: int, name: str, is_public: bool, source_url: str | None, source_type: str | None) -> int:
    """Inserts a new playlist and returns its id."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO playlists (name, owner_id, is_public, source_url, source_type) VALUES (?, ?, ?, ?, ?)",
            (name, user_id, is_public, source_url, source_type),
        )
        await db.commit()
        cursor = await db.execute("SELECT last_insert_rowid()")
        return (await cursor.fetchone())[0]

async def delete_playlist(playlist_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM songs WHERE playlist_id = ?", (playlist_id,))
        await db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        await db.commit()


# ── Songs ──────────────────────────────────────────────────────────────────────

async def get_playlist_songs(playlist_id: int) -> list[tuple]:
    """Returns (id, title, artist, stream_url, duration) ordered by added_at."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, title, artist, stream_url, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
            (playlist_id,),
        )
        return await cursor.fetchall()

async def get_playlist_songs_display(playlist_id: int) -> list[tuple]:
    """Returns (title, artist, duration) for display purposes."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT title, artist, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
            (playlist_id,),
        )
        return await cursor.fetchall()

async def get_mix_songs(user_id: int) -> list[tuple]:
    """Returns all accessible songs in random order for mix mode."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.id, s.title, s.artist, s.stream_url, s.duration
            FROM songs s
            JOIN playlists p ON s.playlist_id = p.id
            WHERE p.owner_id = ? OR p.is_public = 1
            ORDER BY RANDOM()
        """, (user_id,))
        return await cursor.fetchall()

async def add_song_to_playlist(playlist_id: int, title: str, artist: str, stream_url: str, duration: int) -> bool:
    """Insert a song into a playlist. Returns True if inserted, False if duplicate."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO songs (playlist_id, title, artist, stream_url, duration) VALUES (?, ?, ?, ?, ?)",
            (playlist_id, title, artist, stream_url, duration),
        )
        await db.commit()
        return cursor.rowcount > 0

async def set_playlist_privacy(playlist_id: int, is_public: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE playlists SET is_public = ? WHERE id = ?", (is_public, playlist_id)
        )
        await db.commit()

async def get_playlist_songs_with_ids(playlist_id: int) -> list[tuple]:
    """Returns (id, title, artist, duration) for remove-song dropdown."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, title, artist, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
            (playlist_id,),
        )
        return await cursor.fetchall()

async def delete_song(song_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        await db.commit()
