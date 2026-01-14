import aiosqlite
import os

DB_PATH = "data/user.db"

async def init_user_db():
    """Initialize the database with tables"""
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL UNIQUE,
                username TEXT NOT NULL,
                bio TEXT DEFAULT 'This user has no bio set.',
                profile_color TEXT DEFAULT 'gold',
                amber_dabloons INTEGER DEFAULT 0,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # games table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                daily_coin_claim TIMESTAMP,
                last_experience_gain TIMESTAMP,
                duck_clicker_current_score INTEGER DEFAULT 0,
                duck_clicker_high_score INTEGER DEFAULT 0,
                PRIMARY KEY (user_id)
            )
        """)
