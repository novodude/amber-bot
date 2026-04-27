from utils.userbase.database import DB_PATH
from utils.userbase.ensure_registered import ensure_registered
import aiosqlite
import discord

async def increment_ttt_wins(user: discord.User):
    user_id = await ensure_registered(user.id, str(user))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE games
            SET ttt_wins = ttt_wins + 1
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def increment_ttt_wins_streak(user: discord.User):
    user_id = await ensure_registered(user.id, str(user))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE games
            SET ttt_streak = ttt_streak + 1
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def reset_ttt_wins_streak(user: discord.User):
    user_id = await ensure_registered(user.id, str(user))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE games
            SET ttt_streak = 0
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()
