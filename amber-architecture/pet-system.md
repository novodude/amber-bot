# Pet System

A cat companion that lives in the database, decays over time, levels up, and messages its owner when they've been away.

---

## Overview

Each user can adopt one cat. The cat has hunger and happiness stats that decay over time. Feed and play with it to keep it healthy. A background task checks every 30 minutes for inactive owners and sends the cat's check-in message via DM.

---

## Stats & Decay

### Hunger

- Starts at 100, max 100.
- Decays 5 points per hour based on `last_fed` timestamp.
- Replenished by feeding food items.

### Happiness

- Starts at 100, max 100.
- Decays 3 points per hour **only when hunger < 30**.
- Replenished by `/pet play`.

### Applying decay

Decay is computed on-the-fly at read time using `apply_decay()` in `utils/pet.py`. It's never stored as a running value — the stored `hunger` and `happiness` are snapshots from the last interaction, and the elapsed hours since `last_fed`/`last_played` are used to calculate the current values.

```python
hunger, happiness = apply_decay(pet["hunger"], pet["happiness"], last_fed, last_played)
```

### Mood states

| Condition | Mood shown in `/pet status` |
|---|---|
| hunger < 20 | 😿 Starving... please feed me |
| happiness < 30 | 😾 Very unhappy... |
| toy_style == "zoomies" | 😻 ZOOMIES TIME |
| happiness > 80 | 😺 Purring contentedly |
| else | 🐱 Doing okay |

---

## Leveling

- XP is gained from `/pet play` (10–20 XP) and pet candy items.
- Level-up formula: `xp_needed = int(80 * (level ** 1.3))`
- XP resets to 0 on level-up.
- Levels unlock accessory slots: base slots at level 1, Extra 1 at level 5, Extra 2 at level 10.

```python
SLOT_UNLOCKS = {
    1:  ["slot_collar", "slot_bow", "slot_hat", "slot_toy"],
    5:  ["slot_extra1"],
    10: ["slot_extra2"],
}
```

### XP multiplier (collar)

If a collar is equipped, `add_pet_xp` should account for it (currently the multiplier is defined in `get_xp_multiplier()` but not applied automatically — the play command passes a fixed XP gain).

---

## Accessories

| Slot | Items | Effect |
|---|---|---|
| Collar | Red Collar (+10% XP), Gold Collar (+25% XP) | XP multiplier |
| Bow | Silk Bow (+10% dabloons), Diamond Bow (+25% dabloons) | Dabloon drop multiplier |
| Hat | Wizard Hat 🧙, Party Hat 🎉, Crown 👑 | Cosmetic — shown as emoji in status |
| Toy | Yarn Ball, Laser Pointer, Feather Wand | Changes cat message style |
| Extra 1 | (level 5 unlock) | Any accessory |
| Extra 2 | (level 10 unlock) | Any accessory |

### Toy styles

| Toy | `toy_style` returned | Message flavor |
|---|---|---|
| Laser Pointer | `"zoomies"` | Energetic chaos |
| Feather Wand | `"hunt"` | Hunting-focused language |
| Yarn Ball | `"happy"` | Affectionate and content |
| None | `"default"` | Generic affection |

---

## Pet Food Items

| Item | Effect string | Effect |
|---|---|---|
| Kibble | `hunger_20` | +20 hunger |
| Tuna Can | `hunger_50` | +50 hunger |
| Fancy Feast | `hunger_100_hap_10` | +100 hunger, +10 happiness |
| Treat Bag | `happiness_15` | +15 happiness |

The effect string is parsed by `feed_pet()` in `utils/pet.py` by splitting on `_` and reading key-value pairs (`hunger`, `hap`, `happiness`).

---

## Pet Candy

| Item | XP granted |
|---|---|
| XP Candy | 50 |
| Rare Candy | 200 |
| Mega Candy | 500 |

---

## Check-in Messages (Background Task)

`PetCog.check_in_loop` runs every 30 minutes. For each pet whose owner has been inactive for 4+ hours **and** the cat hasn't messaged in the last 6 hours, it:

1. Computes current hunger and happiness with decay.
2. Picks a message style via `pick_style(happiness, hunger, toy_style)`.
3. Generates a message via `build_check_in_message(...)`.
4. Sends the message as a DM to the owner.
5. Updates `pets.last_message_sent`.

Owner activity is tracked via `touch_owner_activity(user_id)`, which is called in `on_message` for every non-bot message.

---

## Cat Message Generation (`utils/cat_model.py`)

### Priority

1. **domesticated-LLM** — if `./domesticated-LLM/` directory exists and torch is available, loads `SmolLM2-135M-Instruct` fine-tuned on 20k cat-speak examples.
2. **Synthesis engine** — always available, no dependencies. Randomly assembles messages from word pools (`_CAT_NOISES`, `_EMOTES`, `_FILLERS`, `_STYLE_POOLS`).

### Style → instruction mapping

The style key (e.g. `"food"`, `"zoomies"`, `"affection"`) maps to a natural-language instruction string for the LLM (`_STYLE_INSTRUCTIONS`), or to a word pool for synthesis (`_STYLE_POOLS`).

### Public API

```python
# Full pipeline — used by commands/pet.py
message = build_check_in_message(
    pet_name="Mochi",
    happiness=45,
    hunger=80,
    toy_style="zoomies",
    owner_context="want to play?"
)

# Low-level — used when you have an explicit instruction and context
raw = generate_cat_message(instruction, context)
```

---

## DB Helpers (`utils/pet.py`)

| Function | What it does |
|---|---|
| `get_pet(user_id)` | Returns pet row as dict, or None |
| `create_pet(user_id, name)` | Inserts a new pet row |
| `update_pet(user_id, **kwargs)` | Updates any columns by keyword |
| `add_pet_xp(user_id, amount)` | Adds XP and handles level-up; returns new level or None |
| `feed_pet(user_id, effect)` | Applies food effect string, updates DB, returns (hunger, happiness) |
| `equip_accessory(user_id, slot, item_name)` | Equips or unequips (None) a slot; returns False if locked |
| `touch_owner_activity(user_id)` | Updates `last_owner_activity` to now |
| `apply_decay(hunger, happiness, last_fed, last_played)` | Pure function — computes current stats |
| `get_unlocked_slots(level)` | Returns list of unlocked slot keys for a given level |
| `get_toy_style(toy)` | Returns style string from toy item name |
| `get_hat_emoji(hat)` | Returns emoji string from hat item name |
| `xp_to_next_level(level)` | Returns XP threshold for next level |
