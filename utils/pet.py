"""utils/pet.py — pet helpers used by commands/pet.py and the background task"""
import aiosqlite
from datetime import datetime
from utils.userbase.database import DB_PATH

# ── Level → slot unlock table ─────────────────────────────────────────────────
# Slots unlocked per level milestone.  Keys are the minimum level required.
SLOT_UNLOCKS = {
    1:  ["slot_collar", "slot_bow", "slot_hat", "slot_toy"],   # base slots
    5:  ["slot_extra1"],
    10: ["slot_extra2"],
}

SLOT_LABELS = {
    "slot_collar": "Collar",
    "slot_bow":    "Bow",
    "slot_hat":    "Hat",
    "slot_toy":    "Toy",
    "slot_extra1": "Extra 1",
    "slot_extra2": "Extra 2",
}

# ── XP needed to level up ─────────────────────────────────────────────────────
def xp_to_next_level(level: int) -> int:
    return int(80 * (level ** 1.3))

# ── Happiness / hunger decay ──────────────────────────────────────────────────
HUNGER_DECAY_PER_HOUR   = 5   # lose 5 hunger per hour
HAPPINESS_DECAY_PER_HOUR = 3  # lose 3 happiness per hour if hunger < 30

def apply_decay(hunger: int, happiness: int, last_fed: datetime, last_played: datetime) -> tuple[int, int]:
    now = datetime.utcnow()
    hours_since_fed   = max(0, (now - last_fed).total_seconds() / 3600)
    hours_since_played = max(0, (now - last_played).total_seconds() / 3600)

    hunger    = max(0, hunger    - int(hours_since_fed    * HUNGER_DECAY_PER_HOUR))
    if hunger < 30:
        happiness = max(0, happiness - int(hours_since_played * HAPPINESS_DECAY_PER_HOUR))

    return hunger, happiness

# ── Accessory effect helpers ──────────────────────────────────────────────────
def get_xp_multiplier(collar: str | None) -> float:
    if collar == "Gold Collar": return 1.25
    if collar == "Red Collar":  return 1.10
    return 1.0

def get_dabloon_multiplier(bow: str | None) -> float:
    if bow == "Diamond Bow": return 1.25
    if bow == "Silk Bow":    return 1.10
    return 1.0

def get_toy_style(toy: str | None) -> str:
    if toy == "Laser Pointer":  return "zoomies"
    if toy == "Feather Wand":   return "hunt"
    if toy == "Yarn Ball":      return "happy"
    return "default"

def get_hat_emoji(hat: str | None) -> str:
    HAT_EMOJIS = {"Wizard Hat": "🧙", "Party Hat": "🎉", "Crown": "👑"}
    return HAT_EMOJIS.get(hat, "")

def get_unlocked_slots(level: int) -> list[str]:
    unlocked = []
    for min_level, slots in SLOT_UNLOCKS.items():
        if level >= min_level:
            unlocked.extend(slots)
    return unlocked

# ── DB helpers ────────────────────────────────────────────────────────────────
async def get_pet(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM pets WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_pet(user_id: int, name: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO pets (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        await db.commit()
    return await get_pet(user_id)

async def update_pet(user_id: int, **kwargs):
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE pets SET {cols} WHERE user_id = ?", vals)
        await db.commit()

async def add_pet_xp(user_id: int, amount: int) -> int | None:
    """Add XP to pet. Returns new level if levelled up, else None."""
    pet = await get_pet(user_id)
    if not pet:
        return None

    new_xp    = pet["experience"] + amount
    new_level = pet["level"]
    levelled  = False

    while new_xp >= xp_to_next_level(new_level):
        new_xp   -= xp_to_next_level(new_level)
        new_level += 1
        levelled   = True

    await update_pet(user_id, experience=new_xp, level=new_level)
    return new_level if levelled else None

async def feed_pet(user_id: int, effect: str) -> tuple[int, int]:
    """Apply food effect. Returns (new_hunger, new_happiness)."""
    pet = await get_pet(user_id)
    if not pet:
        return 0, 0

    last_fed   = datetime.fromisoformat(pet["last_fed"])   if pet["last_fed"]   else datetime.utcnow()
    last_played = datetime.fromisoformat(pet["last_played"]) if pet["last_played"] else datetime.utcnow()
    hunger, happiness = apply_decay(pet["hunger"], pet["happiness"], last_fed, last_played)

    # Parse effect string like "hunger_50" or "hunger_100_hap_10"
    parts = effect.split("_")
    i = 0
    while i < len(parts):
        if parts[i] == "hunger" and i + 1 < len(parts):
            hunger = min(100, hunger + int(parts[i + 1]))
            i += 2
        elif parts[i] == "hap" and i + 1 < len(parts):
            happiness = min(100, happiness + int(parts[i + 1]))
            i += 2
        elif parts[i] == "happiness" and i + 1 < len(parts):
            happiness = min(100, happiness + int(parts[i + 1]))
            i += 2
        else:
            i += 1

    await update_pet(user_id, hunger=hunger, happiness=happiness,
                     last_fed=datetime.utcnow().isoformat())
    return hunger, happiness

async def equip_accessory(user_id: int, slot: str, item_name: str | None) -> bool:
    """Equip or unequip an item in a slot. Returns False if slot locked."""
    pet = await get_pet(user_id)
    if not pet:
        return False
    if slot not in get_unlocked_slots(pet["level"]):
        return False
    await update_pet(user_id, **{slot: item_name})
    return True

async def touch_owner_activity(user_id: int):
    """Call whenever the owner sends a message — resets the inactivity timer."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pets SET last_owner_activity = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id)
        )
        await db.commit()
