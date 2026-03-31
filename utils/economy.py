import aiosqlite
import random

import discord
from utils.userbase.database import DB_PATH

async def add_dabloons(user_id: int, amount: int):
    """Add dabloons to a user's account
    
    Args:
        user_id: The internal database user ID (not discord_id)
        amount: Amount of dabloons to add (can be negative to subtract)
    """
    async with aiosqlite.connect("data/user.db") as db:
        await db.execute(
            "UPDATE users SET amber_dabloons = amber_dabloons + ? WHERE id = ?",
            (amount, user_id)
        )
        await db.commit()

async def get_dabloons(user_id: int) -> int:
    """Get a user's current dabloon balance
    
    Args:
        user_id: The internal database user ID (not discord_id)
        
    Returns:
        Current dabloon balance
    """
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute(
            "SELECT amber_dabloons FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_leaderboard() -> list[tuple[int, int]]:
    """Get the top 10 users by dabloon balance"""
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute(
            "SELECT username, amber_dabloons FROM users ORDER BY amber_dabloons DESC LIMIT 10"
        )
        rows = await cursor.fetchall()
        return rows

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




# ── leveling and xp ─────────────────────────────────────────────────────────────
# uses the database user ID, not the discord ID
async def add_xp(user_id, amount: int | None, message: str | None) -> int | None:
    xp_amount = random.randint(5, 25) if amount is None else amount
    xp_amount = int(xp_amount + len(message)) // 20   if message else xp_amount
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET experience = experience + ? WHERE id = ?',
            (xp_amount, user_id)
        )
        await db.commit()

        cursor = await db.execute(
            'SELECT experience, level FROM users WHERE id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        xp, level = row[0], row[1]
        xp_needed = int(100 * (level ** 1.2))

        if xp >= xp_needed:
            new_level = level + 1
            await db.execute(
                'UPDATE users SET level = ?, experience = 0 WHERE id = ?',
                (new_level, user_id)
            )
            await db.commit()
            return new_level

# uses the database user ID, not the discord ID
async def get_level(user_id) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT level FROM users WHERE id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

# uses the database user ID, not the discord ID
async def get_xp(user_id) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT experience FROM users WHERE id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
