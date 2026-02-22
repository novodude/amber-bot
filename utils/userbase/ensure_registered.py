import aiosqlite
from utils.economy import get_user_id_from_discord

DB_PATH = "data/user.db"


async def ensure_registered(discord_id: int, username: str) -> int:
    """
    Returns the internal user_id for a Discord user.
    If they aren't registered yet, silently registers them with 50 starter dabloons.

    Use this instead of get_user_id_from_discord() in any command that requires registration.
    The user won't see any registration message — it just happens in the background.
    """
    user_id = await get_user_id_from_discord(discord_id)

    if user_id is not None:
        return user_id

    # Not registered — create them now
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO users (discord_id, amber_dabloons, username) VALUES (?, ?, ?)",
            (discord_id, 50, username)
        )
        new_user_id = cursor.lastrowid

        await db.execute(
            "INSERT INTO games (user_id) VALUES (?)",
            (new_user_id,)
        )

        await db.commit()

    return new_user_id
