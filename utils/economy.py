import aiosqlite

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
