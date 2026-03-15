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
                user_id INTEGER PRIMARY KEY,
                daily_coin_claim TIMESTAMP,
                last_experience_gain TIMESTAMP,
                duck_clicker_current_score INTEGER DEFAULT 0,
                duck_clicker_high_score INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_streak INTEGER DEFAULT 0,
                action_use_count INTEGER DEFAULT 0,   -- total /do + /look uses for dabloon tracking
                next_reward_threshold INTEGER DEFAULT 0, -- next milestone to reward at
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                price INTEGER NOT NULL,
                description TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT '!',
            welcome_channel_id INTEGER,
            welcome_message TEXT,
            log_channel_id INTEGER,
            autorole_id INTEGER
            )
        """)

        # ── Action counts ─────────────────────────────────────────────────────
        # Tracks how many times each action has been performed.
        #   actor_id   - internal user ID of whoever ran /do or /look
        #   target_id  - internal user ID of the target (NULL for /look or @everyone)
        #   action     - action/reaction name e.g. 'hug', 'kiss', 'blush'
        #   count      - number of times this actor->target->action combo has occurred
        await db.execute("""
            CREATE TABLE IF NOT EXISTS action_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER NOT NULL,
                target_id INTEGER,
                action TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(actor_id, target_id, action)
            )
        """)

        # Migrate existing games rows that are missing the new columns
        try:
            await db.execute("ALTER TABLE games ADD COLUMN action_use_count INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists
        try:
            await db.execute("ALTER TABLE games ADD COLUMN next_reward_threshold INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists

        await db.commit()
