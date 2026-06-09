# Economy System

Dabloons, XP, leveling, and all the helpers that power them.

---

## Overview

The economy has two parallel tracks:

- **Dabloons** — spendable currency. Earned from daily claims, game wins, reaction milestones, and quests. Spent in the shop and on Tic Tac Toe entry fees.
- **XP / Level** — progression track. Earned from chatting, daily claims, game wins, and quests. Unlocks more daily quests. Not spendable.

---

## Dabloon Sources

| Source | Amount |
|---|---|
| Registration bonus | 50 |
| `/money daily` | 100–200 (random, 24h cooldown) |
| Duck Clicker | 2 per 5 clicks (4 with Double Points upgrade) |
| Tic Tac Toe win | 4 / 8 / 16 (easy / medium / hard) |
| `/do` or `/look` milestone | 5–10 (random, every 5–10 uses) |
| Quest reward | 20–100 depending on quest |

---

## XP Sources

| Source | Amount |
|---|---|
| Chat message | 5–25 XP, scaled by `len(message) // 20` |
| `/money daily` | 40–80 XP (random) |
| Tic Tac Toe win | `reward * 10` XP (40 / 80 / 160) |
| Quest reward | 50–180 XP depending on quest |
| `/pet play` | 10–20 XP for the player |

### Level-up formula

```python
xp_needed = int(100 * (level ** 1.2))
```

Level-up resets `experience` to 0 and increments `level`. A level-up notification embed is sent in the channel where the leveling message was posted (deletes after 10 seconds).

### Quest unlock thresholds

| Level | Daily quests available |
|---|---|
| 1–9 | 3 |
| 10–19 | 4 |
| 20+ | 5 |

---

## Helper Functions (`utils/economy.py`)

### `add_dabloons(user_id, amount)`

Add or subtract dabloons. Takes internal DB user ID. Pass negative to subtract.

```python
await add_dabloons(user_id, 50)    # add
await add_dabloons(user_id, -10)   # subtract
```

Does not guard against going negative — callers must check balance first.

### `get_dabloons(user_id)`

Returns current balance as int.

```python
balance = await get_dabloons(user_id)
```

### `get_user_id_from_discord(discord_id)`

Converts a Discord snowflake to internal `users.id`. Returns `None` if not registered.

```python
user_id = await get_user_id_from_discord(interaction.user.id)
if user_id is None:
    # not registered
```

### `add_xp(user_id, amount, message)`

Adds XP and handles level-up. Pass `amount=None` and a `message` string for chat-based XP (uses random amount scaled by message length). Returns new level as int if levelled up, otherwise returns `None`.

```python
new_level = await add_xp(user_id, None, message.content)   # chat XP
new_level = await add_xp(user_id, 80, None)                  # fixed XP
```

### `get_level(user_id)` / `get_xp(user_id)`

Return current level and current XP as ints.

### `get_leaderboard()`

Returns top 10 `(username, amber_dabloons)` tuples ordered by balance descending.

---

## Registration (`utils/userbase/ensure_registered.py`)

### `ensure_registered(discord_id, username)`

The correct way to handle registration in most commands. If the user exists, returns their `user_id`. If not, silently creates them with 50 starter dabloons and a `games` row, then returns the new `user_id`.

```python
user_id = await ensure_registered(interaction.user.id, str(interaction.user))
```

**When to use `ensure_registered` vs `get_user_id_from_discord`:**

- Use `ensure_registered` in economy, game, pet, and shop commands — you want registration to be invisible.
- Use `get_user_id_from_discord` when you explicitly want to know if someone is registered without creating them (e.g. checking the receiver in `/money give`).

---

## Profile Display (`utils/banking.py`)

`build_profile_embed(discord_id, user, balance, bio, color, greeting_time)` builds the full profile embed including:

- Greeting with time-of-day (morning / afternoon / evening / night based on UTC hour)
- Bio
- Dabloon balance
- Total actions performed
- Hugs and pats received

`ProfileView` is the interactive view attached to `/profile`. Buttons: Refresh, Edit Bio, Customize (color picker dropdown).

### Profile Colors

Default colors are built into `ProfileView.get_color()`: gold, blue, red, green, purple, orange, pink, dark_blue.

Unlockable shop colors: cyan, rose, midnight. These are applied by setting `users.profile_color` to the color name.

Custom hex: requires "Custom Color" shop purchase. Stored in `users.custom_hex_color`. Activates `users.profile_color = 'custom'`.

---

## Dabloon Reward System (`utils/action_counts.py`)

`maybe_reward_dabloons(discord_id)` handles milestone rewards for `/do` and `/look` use.

It increments `games.action_use_count` each call. When `action_use_count >= next_reward_threshold`:

1. Awards 5–10 dabloons randomly
2. Sets `next_reward_threshold = use_count + random.randint(5, 10)`
3. Returns the reward amount

Returns `None` if no reward this time. Call after every `/do` or `/look`.
