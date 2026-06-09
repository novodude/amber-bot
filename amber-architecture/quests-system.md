# Quests System

A daily quest system that refreshes every day and encourages use of different bot features.

---

## Overview

Each day, the bot generates a shared pool of 5 quests from `QUEST_POOL`. Users see a slice of those quests based on their level (3, 4, or 5). Progress is tracked per-user. Completing a quest shows a claim button; claiming awards dabloons and XP.

All logic lives in `utils/quests.py`. The command is in `commands/quests.py`.

---

## Quest Types

| Type | What triggers progress |
|---|---|
| `emoji_use` | Sending the daily emoji in any message |
| `word_use` | Using the daily word in any message (case-insensitive, no word boundary) |
| `ttt_win` | Winning a Tic Tac Toe game |
| `duck_clicks` | Clicking in Duck Clicker |

`emoji_use` and `word_use` progress is tracked automatically in `message_quest_handler()`, which is called in `on_message`.

`ttt_win` and `duck_clicks` are tracked by calling `increment_quest_progress()` directly inside the game commands.

---

## Daily Quest Pool (`QUEST_POOL`)

12 quests total. Every quest has:

```python
{
    "title": "Emoji Spammer",
    "description": "Send {target_value} in your messages {target} times",
    "type": "emoji_use",
    "target": 10,                  # base target (overridden for duck_clicks)
    "reward_dabloons": 20,
    "reward_xp": 50,
    "_tier": 1.0,                  # only for duck_clicks — difficulty multiplier
}
```

### Quest breakdown

| Quest | Type | Target | Reward |
|---|---|---|---|
| Emoji Spammer | emoji_use | 10 | 🪙20 / ✨50 |
| Emoji Addict | emoji_use | 25 | 🪙40 / ✨80 |
| Emoji Machine | emoji_use | 50 | 🪙70 / ✨120 |
| Potty Mouth | word_use | 5 | 🪙25 / ✨60 |
| Word of the Day | word_use | 10 | 🪙40 / ✨90 |
| Broken Record | word_use | 20 | 🪙65 / ✨130 |
| Tic Tac Beginner | ttt_win | 1 | 🪙30 / ✨70 |
| Tic Tac Pro | ttt_win | 3 | 🪙60 / ✨120 |
| Tic Tac Master | ttt_win | 5 | 🪙100 / ✨180 |
| Duck Enthusiast | duck_clicks | scaled | 🪙25 / ✨60 |
| Duck Fanatic | duck_clicks | scaled | 🪙50 / ✨100 |
| Duck Overlord | duck_clicks | scaled | 🪙90 / ✨160 |

---

## Daily Randomization

Each day, `get_or_create_daily_quests()` picks 5 random quest indices from the pool and stores them in `daily_quests` with `date = today`.

For that day's quests, it also picks:
- One **daily emoji** from `EMOJI_POOL` (30 options — intentionally awkward to use: 🍑, 💀, 🤡, etc.)
- One **daily word** from `WORD_POOL` (50 options — intentionally awkward to say: "moist", "squirt", "bogey", etc.)

These are stored in `daily_quests.target_value` for the relevant quest rows.

---

## Duck Clicks Target Scaling

Duck Clicker targets are computed per-user per-day based on their level:

```python
def calculate_duck_target(level: int, tier: float = 1.0) -> int:
    base = int(25 * (level ** 1.3))
    return max(10, int(base * tier))
```

Tiers: Duck Enthusiast = 1.0×, Duck Fanatic = 1.5×, Duck Overlord = 2.2×. The computed value is stored in `user_quests.target_override` when the row is first created.

---

## Quest Count by Level

```python
def get_quest_count_for_level(level: int) -> int:
    if level >= 20: return 5
    if level >= 10: return 4
    return 3
```

---

## Progress Tracking

### `increment_quest_progress(discord_id, quest_type, amount=1)`

Call this whenever a relevant action happens. It:
1. Gets the user's active quests for today.
2. Finds all quests matching `quest_type`.
3. Increments `user_quests.progress` by `amount`, capped at `effective_target`.
4. Sets `completed = 1` if `progress >= target`.

### `message_quest_handler(message)`

Called from `on_message` for every non-bot message. Gets today's daily emoji and word from the DB, counts occurrences in the message, and calls `increment_quest_progress` accordingly.

```python
count = count_specific_emoji(content, daily_emoji)    # exact match
count = count_word_occurrences(content, daily_word)   # regex, case-insensitive
```

---

## Claiming Rewards

`claim_quest(discord_id, daily_quest_id)` validates that the quest is completed and unclaimed, awards dabloons and XP, and marks `claimed = 1`. Returns `(success, message, dabloons, xp)`.

The claim button in `QuestsView` calls this, then refreshes the embed in place and sends an ephemeral reward notification.

---

## UI (`commands/quests.py`)

`QuestsView` builds claim buttons dynamically — one per completed-but-unclaimed quest. When a quest is claimed, the view rebuilds itself and the embed is updated in place.

`build_quests_embed(user, quests)` renders each quest as a field with:
- Title (strikethrough if claimed)
- Description with placeholders filled in
- Progress bar or status text
- Reward summary

Progress bar format: `█████░░░░░ 5/10`
