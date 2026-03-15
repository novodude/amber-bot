import random
import aiosqlite
from utils.economy import get_user_id_from_discord, add_dabloons
from utils.userbase.ensure_registered import ensure_registered

DB_PATH = "data/user.db"


# ── Count helpers ─────────────────────────────────────────────────────────────

async def increment_action_count(actor_discord_id: int, target_discord_id: int | None, action: str) -> int:
    """
    Increment the action count for actor -> target -> action and return the new count.
    target_discord_id can be None for /look or @everyone actions.
    """
    actor_id = await get_user_id_from_discord(actor_discord_id)
    if actor_id is None:
        return 0

    target_id = None
    if target_discord_id is not None:
        target_id = await get_user_id_from_discord(target_discord_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO action_counts (actor_id, target_id, action, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(actor_id, target_id, action)
            DO UPDATE SET count = count + 1
        """, (actor_id, target_id, action))
        await db.commit()

        cursor = await db.execute("""
            SELECT count FROM action_counts
            WHERE actor_id = ? AND target_id IS ? AND action = ?
        """, (actor_id, target_id, action))
        row = await cursor.fetchone()
        return row[0] if row else 1


async def get_action_count(actor_discord_id: int, target_discord_id: int | None, action: str) -> int:
    """Get the current count for actor -> target -> action."""
    actor_id = await get_user_id_from_discord(actor_discord_id)
    if actor_id is None:
        return 0

    target_id = None
    if target_discord_id is not None:
        target_id = await get_user_id_from_discord(target_discord_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT count FROM action_counts
            WHERE actor_id = ? AND target_id IS ? AND action = ?
        """, (actor_id, target_id, action))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_received_count(target_discord_id: int, action: str) -> int:
    """Get total times a user has received a specific action from anyone."""
    target_id = await get_user_id_from_discord(target_discord_id)
    if target_id is None:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT COALESCE(SUM(count), 0) FROM action_counts
            WHERE target_id = ? AND action = ?
        """, (target_id, action))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_total_actions_performed(actor_discord_id: int) -> int:
    """Get total actions performed by a user across all action types."""
    actor_id = await get_user_id_from_discord(actor_discord_id)
    if actor_id is None:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT COALESCE(SUM(count), 0) FROM action_counts
            WHERE actor_id = ?
        """, (actor_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_top_received_actions(target_discord_id: int, limit: int = 3) -> list[tuple[str, int]]:
    """Get the top N most received actions for a user as [(action, count), ...]."""
    target_id = await get_user_id_from_discord(target_discord_id)
    if target_id is None:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT action, SUM(count) as total
            FROM action_counts
            WHERE target_id = ?
            GROUP BY action
            ORDER BY total DESC
            LIMIT ?
        """, (target_id, limit))
        return await cursor.fetchall()


# ── Dabloon reward helper ─────────────────────────────────────────────────────

async def maybe_reward_dabloons(discord_id: int) -> int | None:
    """
    Increment the user's total action use count.
    If they've hit their next reward threshold, award 5-10 dabloons and set a new threshold.
    Returns the amount awarded, or None if no reward this time.
    """
    user_id = await ensure_registered(discord_id, str(discord_id))

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT action_use_count, next_reward_threshold FROM games WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        use_count, threshold = row
        use_count += 1

        if use_count >= threshold:
            reward = random.randint(5, 10)
            new_threshold = use_count + random.randint(5, 10)
            await db.execute("""
                UPDATE games
                SET action_use_count = ?, next_reward_threshold = ?
                WHERE user_id = ?
            """, (use_count, new_threshold, user_id))
            await db.commit()
            await add_dabloons(user_id, reward)
            return reward
        else:
            await db.execute(
                "UPDATE games SET action_use_count = ? WHERE user_id = ?",
                (use_count, user_id)
            )
            await db.commit()
            return None
