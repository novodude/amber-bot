from typing import Literal
import aiosqlite
import random
import discord
from utils.userbase.ensure_registered import ensure_registered

DB_PATH = "data/user.db"

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

async def add_dabloons_to_all(amount: int):
    """Add dabloons to all users' accounts
    
    Args:
        amount: Amount of dabloons to add (can be negative to subtract)
    """
    async with aiosqlite.connect("data/user.db") as db:
        await db.execute(
            "UPDATE users SET amber_dabloons = amber_dabloons + ?",
            (amount,)
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

async def is_private_account(discord_id: int) -> bool:
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute(
            "SELECT is_private FROM users WHERE discord_id = ?",
            (discord_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return False
        return row[0] == 1

async def set_private_account(discord_id: int, is_private: bool):
    async with aiosqlite.connect("data/user.db") as db:
        await db.execute(
            "UPDATE users SET is_private = ? WHERE discord_id = ?",
            (1 if is_private else 0, discord_id)
        )
        await db.commit()

async def clean_leaderboard_data(data: list[tuple[str, int, str]]) -> list[tuple[str, int]]:
    """
    Remove private accounts from leaderboard data and replace discord IDs with mentions.
    """
    cleaned_data = []
    for discord_id, value, username in data:
        if not await is_private_account(discord_id):
            cleaned_data.append((f"@{username}", value, discord_id))
    return cleaned_data

async def get_leaderboard(type: Literal["money", "level", "actions received", "action given", "duck clicker", "ttt", "ttt streak"]) -> list[tuple[int, int]]:
    """Get the top 10 users by dabloon balance"""
    
    if type == "money":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT discord_id, amber_dabloons, username FROM users ORDER BY amber_dabloons DESC LIMIT 10"
            )
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "level":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT discord_id, level, username FROM users ORDER BY level DESC, experience DESC LIMIT 10"
            )
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "actions received":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("""
                SELECT u.discord_id, SUM(ac.count) AS total_received, u.username
                FROM action_counts ac
                JOIN users u ON u.id = ac.target_id
                GROUP BY ac.target_id
                ORDER BY total_received DESC
                LIMIT 10
            """)
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "action given":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("""
                SELECT u.discord_id, SUM(ac.count) AS total_given, u.username
                FROM action_counts ac
                JOIN users u ON u.id = ac.actor_id
                GROUP BY ac.actor_id
                ORDER BY total_given DESC
                LIMIT 10
            """)
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "duck clicker":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("""
                SELECT u.discord_id, g.duck_clicker_current_score AS score, u.username
                FROM games g
                JOIN users u ON u.id = g.user_id
                ORDER BY score DESC
                LIMIT 10
            """)
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "ttt":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("""
                SELECT u.discord_id, g.ttt_wins AS wins, u.username
                FROM games g
                JOIN users u ON u.id = g.user_id
                ORDER BY wins DESC
                LIMIT 10
            """)
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    elif type == "ttt streak":
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("""
                SELECT u.discord_id, g.ttt_streak AS streak, u.username
                FROM games g
                JOIN users u ON u.id = g.user_id
                ORDER BY streak DESC
                LIMIT 10
            """)
            data = await cursor.fetchall()
            return await clean_leaderboard_data(data)

    

# ── leveling and xp ─────────────────────────────────────────────────────────────
async def add_xp(user_id, amount: int | None, message: str | None):
    xp_amount = random.randint(5, 25) if amount is None else amount
    if message:
        xp_amount += len(message) // 20

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
        if row is None:
            return None, 0
        xp, level = row[0], row[1]

        new_level = level
        reward_total = 0
        xp_needed = int(100 * (level ** 1.2))
        while xp >= xp_needed:
            xp -= xp_needed
            new_level += 1
            reward_total += 500 * new_level
            xp_needed = int(100 * (new_level ** 1.2))

        if new_level != level:
            await db.execute(
                'UPDATE users SET level = ?, amber_dabloons = amber_dabloons + ?, experience = ? WHERE id = ?',
                (new_level, reward_total, xp, user_id)
            )
            await db.commit()
            return new_level, reward_total

        return None, 0


async def inform_level_up(interaction: discord.Interaction):
    user_id = await ensure_registered(interaction.user.id, interaction.user.display_name)
    new_level, reward = await add_xp(user_id, None, None)
    if new_level:
        embed = discord.Embed(
            title="Level Up!",
            description=f"You've reached level {new_level}!\nYou gained {reward} debloons as a reward :3\nquack on, {interaction.user.mention}!",
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=embed, delete_after=10, reference=interaction.message)

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

async def get_4k_channel_id(message: discord.Message) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT four_k_channel FROM guild_config WHERE guild_id = ?",
            (message.guild.id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return

    four_k_channel_id = row[0]
    if four_k_channel_id is None:
        return
    return four_k_channel_id

