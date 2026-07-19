import aiosqlite
import os

DB_PATH = "data/user.db"

async def init_user_db():
    """Initialize the database with tables"""
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # ── Users ─────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL UNIQUE,
                username TEXT NOT NULL,
                bio TEXT DEFAULT 'This user has no bio set.',
                profile_color TEXT DEFAULT 'gold',
                custom_hex_color TEXT,
                amber_dabloons INTEGER DEFAULT 0,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Games ─────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                user_id INTEGER PRIMARY KEY,
                daily_coin_claim TIMESTAMP,
                last_experience_gain TIMESTAMP,
                duck_clicker_current_score INTEGER DEFAULT 0,
                duck_clicker_high_score INTEGER DEFAULT 0,
                ttt_wins INTEGER DEFAULT 0,
                ttt_streak INTEGER DEFAULT 0,
                action_use_count INTEGER DEFAULT 0,
                next_reward_threshold INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── Inventory ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── Shop ──────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                price INTEGER NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'misc',
                effect TEXT,
                emoji TEXT DEFAULT '📦'
            )
        """)

        # ── User purchases (active effects/unlocks) ───────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1,
                custom_value TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── Pets ──────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT 'Unnamed Cat',
                level INTEGER NOT NULL DEFAULT 1,
                experience INTEGER NOT NULL DEFAULT 0,
                happiness INTEGER NOT NULL DEFAULT 100,
                hunger INTEGER NOT NULL DEFAULT 100,
                last_fed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_sent TIMESTAMP,
                last_owner_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                slot_collar TEXT,
                slot_bow TEXT,
                slot_hat TEXT,
                slot_toy TEXT,
                slot_extra1 TEXT,
                slot_extra2 TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── Warnings ──────────────────────────────────────────────────────────
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

        # ── Guild config ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '!',
                welcome_channel_id INTEGER,
                welcome_message TEXT,
                log_channel_id INTEGER,
                autorole_id INTEGER,
                pet_channel_id INTEGER
            )
        """)

        # ── Action counts ─────────────────────────────────────────────────────
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

        # ── Daily quests ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_index INTEGER NOT NULL,
                date TEXT NOT NULL,
                target_value TEXT
            )
        """)

        # ── User quest progress ───────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_quests (
                user_id INTEGER NOT NULL,
                daily_quest_id INTEGER NOT NULL,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                claimed INTEGER DEFAULT 0,
                target_override INTEGER,
                PRIMARY KEY (user_id, daily_quest_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (daily_quest_id) REFERENCES daily_quests(id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_inventory_user_item
                ON inventory (user_id, item_name)
            """)

        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS default_mute_update
            AFTER INSERT ON users
            WHEN NEW.mute_update IS 0
            BEGIN
                UPDATE users SET mute_update = 1 WHERE id = NEW.id;
            END
        """)

        # ── migrations in case the db is old ───────────────────────────────────
        migrations = [
            "ALTER TABLE games ADD COLUMN action_use_count INTEGER DEFAULT 0",
            "ALTER TABLE games ADD COLUMN next_reward_threshold INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN custom_hex_color TEXT",
            "ALTER TABLE guild_config ADD COLUMN pet_channel_id INTEGER",
            "ALTER TABLE guild_config ADD COLUMN allow_ai INTEGER DEFAULT 1",
            "ALTER TABLE shop ADD COLUMN category TEXT DEFAULT 'misc'",
            "ALTER TABLE shop ADD COLUMN effect TEXT",
            "ALTER TABLE shop ADD COLUMN emoji TEXT DEFAULT '📦'",
            "ALTER TABLE user_purchases ADD COLUMN purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE user_purchases ADD COLUMN active INTEGER DEFAULT 1",
            "ALTER TABLE user_purchases ADD COLUMN custom_value TEXT",
            "ALTER TABLE users ADD COLUMN is_private INTEGER DEFAULT 0",
            "ALTER TABLE guild_config ADD COLUMN four_k_channel INTEGER",
            "ALTER TABLE users ADD COLUMN mute_update INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN mute_pet INTEGER DEFAULT 0"
        ]

        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        # ── Seed shop items ───────────────────────────────────────────────────
        shop_items = [
            # Games
            ('Auto Clicker',     500,  'Automatically clicks every 60s in Duck Clicker',     'games',        'auto_click',        '🤖'),
            ('Double Points',    750,  'Earn 4 dabloons per 5 clicks instead of 2',          'games',        'double_points',     '✨'),
            ('Custom X Symbol',  300,  'Use ⭐ instead of ❌ in Tic Tac Toe',                'games',        'custom_x',          '⭐'),
            ('Custom O Symbol',  300,  'Use 💫 instead of ⭕ in Tic Tac Toe',               'games',        'custom_o',          '💫'),
            # Pet food
            ('Kibble',           30,   'Basic cat food. Restores 20 hunger',                 'pet_food',     'hunger_20',         '🥣'),
            ('Tuna Can',         80,   'Premium cat food. Restores 50 hunger',               'pet_food',     'hunger_50',         '🐟'),
            ('Fancy Feast',      150,  'Gourmet meal. Restores 100 hunger + 10 happiness',   'pet_food',     'hunger_100_hap_10', '🍱'),
            ('Treat Bag',        50,   'Snacks! +15 happiness',                              'pet_food',     'happiness_15',      '🎁'),
            # Accessories
            ('Red Collar',       200,  'Collar slot. Boosts XP earned by 10%',               'accessory',    'collar_xp_10',      '🔴'),
            ('Gold Collar',      500,  'Collar slot. Boosts XP earned by 25%',               'accessory',    'collar_xp_25',      '🟡'),
            ('Silk Bow',         200,  'Bow slot. Boosts dabloon drops by 10%',              'accessory',    'bow_dab_10',        '🎀'),
            ('Diamond Bow',      500,  'Bow slot. Boosts dabloon drops by 25%',              'accessory',    'bow_dab_25',        '💎'),
            ('Wizard Hat',       350,  'Hat slot. Shown on your profile embed',              'accessory',    'hat_cosmetic',      '🧙'),
            ('Party Hat',        150,  'Hat slot. Shown on your profile embed',              'accessory',    'hat_cosmetic',      '🎉'),
            ('Crown',            800,  'Hat slot. Shown on your profile embed',              'accessory',    'hat_cosmetic',      '👑'),
            ('Yarn Ball',        200,  'Toy slot. Pet happier, unlocks playful messages',    'accessory',    'toy_happy',         '🧶'),
            ('Laser Pointer',    300,  'Toy slot. Pet sends zoomies messages',               'accessory',    'toy_zoomies',       '🔴'),
            ('Feather Wand',     250,  'Toy slot. Pet references hunting in messages',       'accessory',    'toy_hunt',          '🪶'),
            # Candy
            ('XP Candy',         100,  'Gives your pet 50 XP',                               'candy',        'pet_xp_50',         '🍬'),
            ('Rare Candy',       300,  'Gives your pet 200 XP',                              'candy',        'pet_xp_200',        '🍭'),
            ('Mega Candy',       700,  'Gives your pet 500 XP — big level jumps possible',   'candy',        'pet_xp_500',        '🌈'),
            # Profile colors
            ('Cyan Theme',       400,  'Unlocks cyan as a profile color',                    'profile_color','color_cyan',        '🩵'),
            ('Rose Theme',       400,  'Unlocks rose as a profile color',                    'profile_color','color_rose',        '🌸'),
            ('Midnight Theme',   400,  'Unlocks midnight black as a profile color',          'profile_color','color_midnight',    '🌑'),
            ('Custom Color',    1000,  'Unlock any hex color for your profile',              'profile_color','color_custom',      '🎨'),
        ]
        await db.executemany("""
            INSERT OR IGNORE INTO shop (item_name, price, description, category, effect, emoji)
            VALUES (?, ?, ?, ?, ?, ?)
        """, shop_items)


        await db.commit()


async def check_update_muted(user_id):
    """Check if the user has muted profile updates"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT mute_update FROM users WHERE discord_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row and row[0] == 1

async def check_pet_muted(user_id):
    """Check if the user has muted pet messages"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT mute_pet FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return row and row[0] == 1
        
async def switch_update_muted(user_id):
    """Toggle the user's profile update mute setting"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT mute_update FROM users WHERE discord_id = ?", (user_id,))
        row = await cursor.fetchone()
        new_value = 0 if row and row[0] == 1 else 1
        await db.execute("UPDATE users SET mute_update = ? WHERE discord_id = ?", (new_value, user_id))
        await db.commit()
        return new_value == 1

async def switch_pet_muted(user_id):
    """Toggle the user's pet message mute setting"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT mute_pet FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        new_value = 0 if row and row[0] == 1 else 1
        await db.execute("UPDATE users SET mute_pet = ? WHERE id = ?", (new_value, user_id))
        await db.commit()
        return new_value == 1

async def get_user_info(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        # User + game stats
        async with db.execute("""
            SELECT
                u.id,
                u.bio,
                u.amber_dabloons,
                u.level,
                g.ttt_wins,
                g.ttt_streak,
                g.duck_clicker_current_score
            FROM users u
            LEFT JOIN games g ON u.id = g.user_id
            WHERE u.discord_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        async with db.execute("""
            SELECT COALESCE(SUM(count), 0)
            FROM action_counts
            WHERE actor_id = ? OR target_id = ?
        """, (user_id, user_id)) as cursor:
            action_row = await cursor.fetchone()

        return {
            "id": row[0],
            "bio": row[1],
            "level": row[3],
            "amber_dabloons": row[2],
            "total_actions": action_row[0],
            "ttt_wins": row[3],
            "ttt_streak": row[4],
            "duck_clicker_score": row[5]
        }

async def list_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT discord_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_userbase_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), AVG(level), SUM(amber_dabloons), AVG(amber_dabloons) FROM users") as cursor:
            row = await cursor.fetchone()
            return {
                "total_users": row[0],
                "average_level": row[1] or 0,
                "total_dabloons": row[2] or 0,
                "average_dabloons": row[3] or 0
            }

async def set_bio(user_id: int, bio: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bio = ? WHERE discord_id = ?", (bio, user_id))
        await db.commit()

async def get_bio(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT bio FROM users WHERE discord_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else "This user has no bio set."

async def clear_bio(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bio = ? WHERE discord_id = ?",
            ("This user has no bio set.", user_id)
        )
        await db.commit()

async def get_profile_data(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT bio, profile_color, custom_hex_color FROM users WHERE discord_id = ?",
            (user_id)
        )
        row = await cursor.fetchone()
        return {
            "bio": row[0] if row else None,
            "profile_color": row[1] if row else None,
            "custom_hex_color": row[2] if row else None
        }

async def set_profile_color(user_id: int, color: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET profile_color = ? WHERE discord_id = ?",
            (color, user_id)
        )
        await db.commit()

async def has_custom_color(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM user_purchases WHERE user_id = (SELECT id FROM users WHERE discord_id = ?) AND item_name = 'Custom Color' AND active = 1",
            (user_id)
        )
        has_custom = await cursor.fetchone() is not None
        return has_custom

async def get_user_id_from_discord(discord_id: int) -> int | None:
    """Convert Discord ID to internal user ID
    
    Args:
        discord_id: The Discord user's ID
        
    Returns:
        Internal user ID or None if not found
    """
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE discord_id = ?",
            (discord_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def can_amber_speak_in_server(guild_id: int) -> bool:

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT allow_ai FROM guild_config WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cursor.fetchone()
        return row[0] == 1 if row else True

async def set_amber_speaking_permission(guild_id: int, allow: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO guild_config (guild_id, allow_ai) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET allow_ai = ?",
            (guild_id, 1 if allow else 0, 1 if allow else 0)
        )
        await db.commit()
