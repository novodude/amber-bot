import re
import random
import discord
import aiosqlite
from datetime import date
from utils.userbase.database import DB_PATH
from utils.economy import add_dabloons, add_xp, get_user_id_from_discord, get_level
from utils.userbase.ensure_registered import ensure_registered

# ── Emoji pool ────────────────────────────────────────────────────────────────
# funny/embarrassing standard unicode emoji — awkward to spam in chat
EMOJI_POOL = [
    "🍑",  # peach
    "🍆",  # eggplant
    "💦",  # sweat droplets
    "🥵",  # hot face
    "🤤",  # drooling face
    "😳",  # flushed face
    "🥴",  # woozy face
    "🫠",  # melting face
    "💀",  # skull
    "🤡",  # clown face
    "🫃",  # pregnant man
    "🧌",  # troll
    "💩",  # pile of poo
    "🫵",  # index pointing at viewer
    "🤏",  # pinching hand
    "🦶",  # foot
    "👅",  # tongue
    "🫦",  # biting lip
    "🙈",  # see-no-evil monkey
    "😬",  # grimacing face
    "🤢",  # nauseated face
    "🥸",  # disguised face
    "🫁",  # lungs
    "🦠",  # microbe
    "🪣",  # bucket
    "🧻",  # roll of paper
    "🧅",  # onion
    "🫏",  # donkey
    "🪱",  # worm
    "🫨",  # shaking face
]

# ── Word pool ─────────────────────────────────────────────────────────────────
# funny/embarrassing words — awkward to type repeatedly in chat
WORD_POOL = [
    "moist", "squirt", "chunk", "flop", "blobfish",
    "slurp", "crusty", "soggy", "burp", "snort",
    "pudgy", "wobble", "grunt", "lumpy", "drool",
    "gooey", "mucus", "plop", "splat", "sludge",
    "chubby", "dribble", "phlegm", "bogey", "squelch",
    "toot", "jiggly", "bloated", "sweaty", "grimy",
    "goober", "dweeb", "doofus", "gassy", "blorp",
    "gurgle", "snuffle", "schmuck", "skidmark", "flabby",
    "noogie", "wedgie", "booger", "belch", "stinky",
    "sploosh", "gargle", "hiccup", "crusty", "rancid",
]

# ── Quest pool ────────────────────────────────────────────────────────────────
# type options:
#   emoji_use   - use the daily specific emoji N times in messages
#   word_use    - use the daily target word N times in messages (no spaces required)
#   ttt_win     - win N tic tac toe games
#   duck_clicks - click N times in duck clicker today (target set per user via target_override)
#
# description placeholders:
#   {target}       - the numeric goal (from quest pool or effective_target)
#   {target_value} - the daily emoji or word
QUEST_POOL = [
    # emoji quests
    {"title": "Emoji Spammer",    "description": "Send {target_value} in your messages {target} times",  "type": "emoji_use",   "target": 10,  "reward_dabloons": 20,  "reward_xp": 50},
    {"title": "Emoji Addict",     "description": "Send {target_value} in your messages {target} times",  "type": "emoji_use",   "target": 25,  "reward_dabloons": 40,  "reward_xp": 80},
    {"title": "Emoji Machine",    "description": "Send {target_value} in your messages {target} times",  "type": "emoji_use",   "target": 50,  "reward_dabloons": 70,  "reward_xp": 120},
    # word quests
    {"title": "Potty Mouth",      "description": "Say **{target_value}** {target} times in chat",        "type": "word_use",    "target": 5,   "reward_dabloons": 25,  "reward_xp": 60},
    {"title": "Word of the Day",  "description": "Say **{target_value}** {target} times in chat",        "type": "word_use",    "target": 10,  "reward_dabloons": 40,  "reward_xp": 90},
    {"title": "Broken Record",    "description": "Say **{target_value}** {target} times in chat",        "type": "word_use",    "target": 20,  "reward_dabloons": 65,  "reward_xp": 130},
    # ttt quests
    {"title": "Tic Tac Beginner", "description": "Win {target} Tic Tac Toe game",                        "type": "ttt_win",     "target": 1,   "reward_dabloons": 30,  "reward_xp": 70},
    {"title": "Tic Tac Pro",      "description": "Win {target} Tic Tac Toe games",                       "type": "ttt_win",     "target": 3,   "reward_dabloons": 60,  "reward_xp": 120},
    {"title": "Tic Tac Master",   "description": "Win {target} Tic Tac Toe games",                       "type": "ttt_win",     "target": 5,   "reward_dabloons": 100, "reward_xp": 180},
    # duck clicker quests — target always from user_quests.target_override
    {"title": "Duck Enthusiast",  "description": "Click {target} times in Duck Clicker today",           "type": "duck_clicks", "target": 0,   "reward_dabloons": 25,  "reward_xp": 60,  "_tier": 1.0},
    {"title": "Duck Fanatic",     "description": "Click {target} times in Duck Clicker today",           "type": "duck_clicks", "target": 0,   "reward_dabloons": 50,  "reward_xp": 100, "_tier": 1.5},
    {"title": "Duck Overlord",    "description": "Click {target} times in Duck Clicker today",           "type": "duck_clicks", "target": 0,   "reward_dabloons": 90,  "reward_xp": 160, "_tier": 2.2},
]


def calculate_duck_target(level: int, tier: float = 1.0) -> int:
    """Exponential duck click target scaled by level and difficulty tier."""
    base = int(25 * (level ** 1.3))
    return max(10, int(base * tier))


def get_quest_count_for_level(level: int) -> int:
    """How many daily quests a user unlocks based on their level."""
    if level >= 20:
        return 5
    elif level >= 10:
        return 4
    return 3


def format_quest_description(quest: dict) -> str:
    """Fill in description placeholders for display."""
    target_value = quest.get("target_value") or "???"
    effective_target = quest.get("effective_target", quest["target"])
    return quest["description"].format(
        target=effective_target,
        target_value=target_value,
    )


# ── Daily quest management ────────────────────────────────────────────────────

async def get_or_create_daily_quests() -> list[dict]:
    """
    Return today's shared daily quests, creating them if they don't exist yet.
    Always picks 5 — level determines how many a user actually sees.
    """
    today = date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, quest_index, target_value FROM daily_quests WHERE date = ?",
            (today,)
        )
        rows = await cursor.fetchall()

        if not rows:
            indices = random.sample(range(len(QUEST_POOL)), min(5, len(QUEST_POOL)))
            daily_word = random.choice(WORD_POOL)
            daily_emoji = random.choice(EMOJI_POOL)

            for idx in indices:
                quest_type = QUEST_POOL[idx]["type"]
                if quest_type == "word_use":
                    value = daily_word
                elif quest_type == "emoji_use":
                    value = daily_emoji
                else:
                    value = None

                await db.execute(
                    "INSERT INTO daily_quests (quest_index, date, target_value) VALUES (?, ?, ?)",
                    (idx, today, value)
                )

            await db.commit()

            cursor = await db.execute(
                "SELECT id, quest_index, target_value FROM daily_quests WHERE date = ?",
                (today,)
            )
            rows = await cursor.fetchall()

    result = []
    for daily_quest_id, quest_index, target_value in rows:
        quest = dict(QUEST_POOL[quest_index])
        quest["daily_quest_id"] = daily_quest_id
        quest["target_value"] = target_value
        result.append(quest)

    return result


async def get_user_daily_quests(discord_id: int) -> list[dict]:
    """
    Get today's quests for this user, sliced by their level.
    Initializes user_quests rows on first access.
    Sets target_override for duck_clicks quests based on level at first view.
    """
    user_id = await get_user_id_from_discord(discord_id)
    if user_id is None:
        return []

    level = await get_level(user_id)
    quest_count = get_quest_count_for_level(level)
    all_quests = await get_or_create_daily_quests()
    user_quests = all_quests[:quest_count]

    async with aiosqlite.connect(DB_PATH) as db:
        for quest in user_quests:
            daily_quest_id = quest["daily_quest_id"]

            cursor = await db.execute(
                "SELECT progress, completed, claimed, target_override FROM user_quests WHERE user_id = ? AND daily_quest_id = ?",
                (user_id, daily_quest_id)
            )
            row = await cursor.fetchone()

            if not row:
                target_override = None
                if quest["type"] == "duck_clicks":
                    tier = quest.get("_tier", 1.0)
                    target_override = calculate_duck_target(level, tier)

                await db.execute(
                    "INSERT INTO user_quests (user_id, daily_quest_id, target_override) VALUES (?, ?, ?)",
                    (user_id, daily_quest_id, target_override)
                )
                quest["progress"] = 0
                quest["completed"] = False
                quest["claimed"] = False
                quest["effective_target"] = target_override if target_override is not None else quest["target"]
            else:
                progress, completed, claimed, target_override = row
                quest["progress"] = progress
                quest["completed"] = bool(completed)
                quest["claimed"] = bool(claimed)
                quest["effective_target"] = target_override if target_override is not None else quest["target"]

        await db.commit()

    return user_quests


# ── Progress tracking ─────────────────────────────────────────────────────────

async def increment_quest_progress(discord_id: int, quest_type: str, amount: int = 1):
    """
    Increment progress for all of today's matching quests for this user.
    Caps at effective_target, skips already completed quests.
    """
    user_id = await get_user_id_from_discord(discord_id)
    if user_id is None:
        return

    await get_user_daily_quests(discord_id)  # ensure rows exist

    level = await get_level(user_id)
    quest_count = get_quest_count_for_level(level)
    all_quests = await get_or_create_daily_quests()
    user_quests = all_quests[:quest_count]

    async with aiosqlite.connect(DB_PATH) as db:
        for quest in user_quests:
            if quest["type"] != quest_type:
                continue

            daily_quest_id = quest["daily_quest_id"]

            cursor = await db.execute(
                "SELECT progress, completed, target_override FROM user_quests WHERE user_id = ? AND daily_quest_id = ?",
                (user_id, daily_quest_id)
            )
            row = await cursor.fetchone()
            if not row or row[1]:
                continue

            progress, _, target_override = row
            target = target_override if target_override is not None else quest["target"]
            new_progress = min(progress + amount, target)
            new_completed = 1 if new_progress >= target else 0

            await db.execute("""
                UPDATE user_quests SET progress = ?, completed = ?
                WHERE user_id = ? AND daily_quest_id = ?
            """, (new_progress, new_completed, user_id, daily_quest_id))

        await db.commit()


# ── Quest claiming ────────────────────────────────────────────────────────────

async def claim_quest(discord_id: int, daily_quest_id: int) -> tuple[bool, str, int, int]:
    """
    Claim a completed quest reward.
    Returns (success, message, dabloons_rewarded, xp_rewarded).
    """
    user_id = await ensure_registered(discord_id, str(discord_id))
    quests = await get_or_create_daily_quests()

    quest = next((q for q in quests if q["daily_quest_id"] == daily_quest_id), None)
    if not quest:
        return False, "Quest not found.", 0, 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT progress, completed, claimed FROM user_quests WHERE user_id = ? AND daily_quest_id = ?",
            (user_id, daily_quest_id)
        )
        row = await cursor.fetchone()

    if not row or not row[1]:
        return False, "You haven't completed this quest yet!", 0, 0
    if row[2]:
        return False, "You already claimed this quest!", 0, 0

    dabloons = quest["reward_dabloons"]
    xp = quest["reward_xp"]

    await add_dabloons(user_id, dabloons)
    await add_xp(user_id, xp, None)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_quests SET claimed = 1 WHERE user_id = ? AND daily_quest_id = ?",
            (user_id, daily_quest_id)
        )
        await db.commit()

    return True, "Reward claimed!", dabloons, xp


# ── Message tracking helpers ──────────────────────────────────────────────────

def count_specific_emoji(text: str, emoji: str) -> int:
    """Count how many times a specific emoji appears in a message."""
    return text.count(emoji)


def count_word_occurrences(text: str, word: str) -> int:
    """Count occurrences of a word in text, case insensitive, no spaces required."""
    return len(re.findall(re.escape(word.lower()), text.lower()))


async def get_daily_targets() -> tuple[str | None, str | None]:
    """Get today's target emoji and target word from the daily_quests table."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT quest_index, target_value FROM daily_quests WHERE date = ?",
            (today,)
        )
        rows = await cursor.fetchall()

    daily_emoji = None
    daily_word = None

    for quest_index, target_value in rows:
        if target_value is None:
            continue
        quest_type = QUEST_POOL[quest_index]["type"]
        if quest_type == "emoji_use":
            daily_emoji = target_value
        elif quest_type == "word_use":
            daily_word = target_value

    return daily_emoji, daily_word


async def message_quest_handler(message: discord.Message):
    """Call from on_message to track emoji_use and word_use quest progress."""
    content = message.content or ""
    daily_emoji, daily_word = await get_daily_targets()

    if daily_emoji:
        count = count_specific_emoji(content, daily_emoji)
        if count > 0:
            await increment_quest_progress(message.author.id, "emoji_use", amount=count)

    if daily_word:
        count = count_word_occurrences(content, daily_word)
        if count > 0:
            await increment_quest_progress(message.author.id, "word_use", amount=count)
