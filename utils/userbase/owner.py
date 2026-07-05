import aiosqlite
import discord
import os

DB_PATH = "data/owner.db"

async def init_owner_db():
    if not os.path.exists(DB_PATH):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    role TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    update_channel_id INTEGER,
                    log_channel_id INTEGER
                 );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS inbox_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unread',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP

                )
            """)
            
            await db.commit()


async def add_user(user_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO user (user_id, role) VALUES (?, ?)", (user_id, role))
        await db.commit()

async def remove_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user WHERE user_id = ?", (user_id,))
        await db.commit()

async def list_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM user WHERE role = 'owner'") as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def is_owner(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM user WHERE user_id = ? AND role = 'owner'", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result is not None

async def log_action(interaction: discord.Interaction, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO log (action) VALUES (?)", (action,))
        await db.commit()
    log_channel_id = await get_log_channel()
    if log_channel_id:
        log_channel = interaction.client.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(title="Action Logged", description=action, color=discord.Color.blue())
            await log_channel.send(embed=embed)

async def set_update_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO config (id, update_channel_id)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET
            update_channel_id = excluded.update_channel_id
        """, (channel_id,))
        await db.commit()

async def set_log_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO config (id, log_channel_id)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET
            log_channel_id = excluded.log_channel_id
        """, (channel_id,))
        await db.commit()

async def get_log_channel() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT log_channel_id FROM config WHERE id = 1") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def get_update_channel() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT update_channel_id FROM config WHERE id = 1") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def create_inbox_message(user_id: int, message: str, interaction: discord.Interaction) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO inbox_chats (owner_id, user_id, message) VALUES (NULL, ?, ?)", (user_id, message))
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            result = await cursor.fetchone()
        await db.commit()
        await log_action(interaction, f"New inbox message from user {user_id}")
        return result[0] if result else None

async def claim_inbox_message(inbox_id: int, owner_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE inbox_chats SET owner_id = ? WHERE id = ?", (owner_id, inbox_id))
        await db.commit()

async def is_inbox_claimed(inbox_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT owner_id FROM inbox_chats WHERE id = ?", (inbox_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] is not None if result else False

async def get_inbox_message(inbox_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, owner_id, user_id, message, status, timestamp FROM inbox_chats WHERE id = ?", (inbox_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "owner_id": result[1],
                    "user_id": result[2],
                    "message": result[3],
                    "status": result[4],
                    "timestamp": result[5]
                }
            return None

async def get_inbox_status(inbox_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status FROM inbox_chats WHERE id = ?", (inbox_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def list_inbox_messages(status: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        if status:
            async with db.execute("SELECT id, owner_id, user_id, message, status, timestamp FROM inbox_chats WHERE status = ?", (status,)) as cursor:
                return [dict(zip(["id", "owner_id", "user_id", "message", "status", "timestamp"], row)) for row in await cursor.fetchall()]
        else:
            async with db.execute("SELECT id, owner_id, user_id, message, status, timestamp FROM inbox_chats") as cursor:
                return [dict(zip(["id", "owner_id", "user_id", "message", "status", "timestamp"], row)) for row in await cursor.fetchall()]

async def update_inbox_status(inbox_id: int, new_status: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE inbox_chats SET status = ? WHERE id = ?", (new_status, inbox_id))
            await db.commit()
    except Exception:
        return False
    return True
