"""Tests for the bugs fixed on the pets branch."""
import sys
import types
import pathlib

# Add repo root to path so "utils" and "commands" are importable
REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _stub_userbase_db():
    """Register a minimal utils.userbase.database stub (in-memory, no file I/O)."""
    if "utils.userbase.database" not in sys.modules:
        db_mod = types.ModuleType("utils.userbase.database")
        db_mod.DB_PATH = ":memory:"
        sys.modules["utils.userbase.database"] = db_mod


# ── Test 1: reactions.py imports Optional and random ─────────────────────────

def test_reactions_imports_optional_and_random():
    """utils/reactions.py must contain imports for both Optional and random.

    Before the fix, Optional and random were used but never imported,
    causing NameError the first time React_back was instantiated or its
    button was pressed.
    """
    source = (REPO_ROOT / "utils" / "reactions.py").read_text()

    assert "import random" in source, "random must be imported in utils/reactions.py"
    assert "from typing import Optional" in source, (
        "Optional must be imported from typing in utils/reactions.py"
    )


# ── Test 2: check-in SQL query has no cartesian-product JOIN ─────────────────

def test_no_cartesian_guild_config_join():
    """The check-in loop SQL must NOT use `LEFT JOIN guild_config ON 1=1`.

    That pattern joins every pet row with every guild_config row (cartesian
    product) and causes duplicate check-in messages for each configured guild.
    """
    source = (REPO_ROOT / "commands" / "pet.py").read_text()

    assert "ON 1=1" not in source, (
        "Cartesian JOIN 'ON 1=1' must be removed from commands/pet.py"
    )


# ── Test 3: apply_decay behaves correctly ─────────────────────────────────────

def test_apply_decay_no_time_passed():
    """With zero elapsed time, hunger and happiness should not change."""
    _stub_userbase_db()
    from utils.pet import apply_decay
    from datetime import datetime

    now = datetime.utcnow()
    hunger_in, happiness_in = 80, 70
    hunger_out, happiness_out = apply_decay(hunger_in, happiness_in, now, now)

    assert hunger_out == hunger_in, "Hunger should not decay if no time has passed"
    assert happiness_out == happiness_in, "Happiness should not decay if no time has passed"


def test_apply_decay_hunger_decreases():
    """Hunger should decrease by HUNGER_DECAY_PER_HOUR per hour elapsed."""
    _stub_userbase_db()
    from utils.pet import apply_decay, HUNGER_DECAY_PER_HOUR
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    two_hours_ago = now - timedelta(hours=2)
    hunger_in, happiness_in = 80, 70

    hunger_out, _ = apply_decay(hunger_in, happiness_in, two_hours_ago, now)

    expected = max(0, hunger_in - 2 * HUNGER_DECAY_PER_HOUR)
    assert hunger_out == expected, (
        f"Expected hunger {expected} after 2 hours, got {hunger_out}"
    )


def test_apply_decay_hunger_never_negative():
    """Hunger should clamp to zero, never go negative."""
    _stub_userbase_db()
    from utils.pet import apply_decay
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    long_ago = now - timedelta(hours=1000)
    hunger_out, _ = apply_decay(100, 100, long_ago, now)
    assert hunger_out == 0


# ── Test 4: feed_pet effect parsing ──────────────────────────────────────────

def test_feed_effect_hunger_only():
    """Effect 'hunger_50' should add 50 hunger (capped at 100)."""
    hunger = 50
    effect = "hunger_50"
    parts = effect.split("_")
    i = 0
    while i < len(parts):
        if parts[i] == "hunger" and i + 1 < len(parts):
            hunger = min(100, hunger + int(parts[i + 1]))
            i += 2
        else:
            i += 1
    assert hunger == 100, "hunger_50 applied to 50 should give 100 (capped)"


def test_feed_effect_combined():
    """Effect 'hunger_100_hap_10' should add both hunger and happiness."""
    hunger, happiness = 30, 60
    effect = "hunger_100_hap_10"
    parts = effect.split("_")
    i = 0
    while i < len(parts):
        if parts[i] == "hunger" and i + 1 < len(parts):
            hunger = min(100, hunger + int(parts[i + 1]))
            i += 2
        elif parts[i] == "hap" and i + 1 < len(parts):
            happiness = min(100, happiness + int(parts[i + 1]))
            i += 2
        else:
            i += 1
    assert hunger == 100
    assert happiness == 70


# ── Test 5: xp_to_next_level is monotonically increasing ─────────────────────

def test_xp_to_next_level_increases():
    """Each higher level should require more XP than the previous."""
    _stub_userbase_db()
    from utils.pet import xp_to_next_level

    prev = 0
    for level in range(1, 20):
        needed = xp_to_next_level(level)
        assert needed > prev, (
            f"Level {level} should need more XP than level {level - 1}"
        )
        prev = needed


# ── Test 6: get_unlocked_slots returns correct slots per level ────────────────

def test_get_unlocked_slots_level_1():
    _stub_userbase_db()
    from utils.pet import get_unlocked_slots
    slots = get_unlocked_slots(1)
    assert "slot_collar" in slots
    assert "slot_bow" in slots
    assert "slot_hat" in slots
    assert "slot_toy" in slots
    assert "slot_extra1" not in slots
    assert "slot_extra2" not in slots


def test_get_unlocked_slots_level_5():
    _stub_userbase_db()
    from utils.pet import get_unlocked_slots
    slots = get_unlocked_slots(5)
    assert "slot_extra1" in slots
    assert "slot_extra2" not in slots


def test_get_unlocked_slots_level_10():
    _stub_userbase_db()
    from utils.pet import get_unlocked_slots
    slots = get_unlocked_slots(10)
    assert "slot_extra1" in slots
    assert "slot_extra2" in slots


# ── Test 7: accessory effect helpers ─────────────────────────────────────────

def test_xp_multiplier_defaults():
    _stub_userbase_db()
    from utils.pet import get_xp_multiplier
    assert get_xp_multiplier(None) == 1.0
    assert get_xp_multiplier("Red Collar") == 1.10
    assert get_xp_multiplier("Gold Collar") == 1.25


def test_dabloon_multiplier_defaults():
    _stub_userbase_db()
    from utils.pet import get_dabloon_multiplier
    assert get_dabloon_multiplier(None) == 1.0
    assert get_dabloon_multiplier("Silk Bow") == 1.10
    assert get_dabloon_multiplier("Diamond Bow") == 1.25
