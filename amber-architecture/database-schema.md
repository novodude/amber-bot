# Database Schema

Amber uses two SQLite databases. Both are created automatically on first run.

---

## `data/user.db`

Initialized in `utils/userbase/database.py` → `init_user_db()`.

---

### `users`

Core user record. Created on first registration (via `ensure_registered`).

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | INTEGER PK | autoincrement | Internal user ID used everywhere else |
| `discord_id` | INTEGER UNIQUE | — | Raw Discord snowflake |
| `username` | TEXT | — | Discord display name at registration time |
| `bio` | TEXT | `'This user has no bio set.'` | Shown on `/profile` |
| `profile_color` | TEXT | `'gold'` | Color name or `'custom'` |
| `custom_hex_color` | TEXT | NULL | Set when profile_color is `'custom'` |
| `amber_dabloons` | INTEGER | 0 | Currency balance |
| `experience` | INTEGER | 0 | XP toward next level (resets on level-up) |
| `level` | INTEGER | 1 | Current level |
| `created_at` | TIMESTAMP | now | Registration timestamp |

---

### `games`

Per-user game and economy state. One row per user, created alongside the `users` row.

| Column | Type | Default | Notes |
|---|---|---|---|
| `user_id` | INTEGER PK FK | — | References `users.id` |
| `daily_coin_claim` | TIMESTAMP | NULL | Last time `/money daily` was claimed |
| `last_experience_gain` | TIMESTAMP | NULL | Unused (legacy) |
| `duck_clicker_current_score` | INTEGER | 0 | All-time click count |
| `duck_clicker_high_score` | INTEGER | 0 | Unused (legacy) |
| `ttt_wins` | INTEGER | 0 | Unused (tracked via quests instead) |
| `ttt_streak` | INTEGER | 0 | Unused |
| `action_use_count` | INTEGER | 0 | Cumulative `/do`+`/look` uses for dabloon rewards |
| `next_reward_threshold` | INTEGER | 0 | Next action count that triggers a dabloon reward |

---

### `inventory`

Consumable and accessory items owned by a user.

| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER FK | References `users.id` |
| `item_name` | TEXT | Canonical item name from `shop.item_name` |
| `quantity` | INTEGER | Decremented on use |

Primary key is `(user_id, item_name)`. Upsert-safe with `ON CONFLICT DO UPDATE`.

---

### `shop`

Static item catalog. Seeded by `init_user_db()` — rows are inserted with `INSERT OR IGNORE`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `item_name` | TEXT UNIQUE | Canonical name used as identifier |
| `price` | INTEGER | Dabloon cost |
| `description` | TEXT | Shown in `/shop browse` |
| `category` | TEXT | `games`, `pet_food`, `accessory`, `candy`, `profile_color` |
| `effect` | TEXT | Machine-readable effect code (see Shop System) |
| `emoji` | TEXT | Displayed in shop embed |

---

### `user_purchases`

Permanent unlocks (one-time buys like game upgrades and profile color themes).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `user_id` | INTEGER FK | References `users.id` |
| `item_name` | TEXT | — |
| `purchased_at` | TIMESTAMP | — |
| `active` | INTEGER | 1 = active, 0 = revoked |
| `custom_value` | TEXT | Used for custom hex color storage |

---

### `pets`

One row per user who has adopted a cat.

| Column | Type | Default | Notes |
|---|---|---|---|
| `id` | INTEGER PK | — | — |
| `user_id` | INTEGER UNIQUE FK | — | One pet per user |
| `name` | TEXT | `'Unnamed Cat'` | — |
| `level` | INTEGER | 1 | — |
| `experience` | INTEGER | 0 | Toward `xp_to_next_level(level)` |
| `happiness` | INTEGER | 100 | 0–100 |
| `hunger` | INTEGER | 100 | 0–100 |
| `last_fed` | TIMESTAMP | now | Used to compute hunger decay |
| `last_played` | TIMESTAMP | now | Used to compute happiness decay |
| `last_message_sent` | TIMESTAMP | NULL | Last time the pet DM'd the owner |
| `last_owner_activity` | TIMESTAMP | now | Updated on every owner message |
| `slot_collar` | TEXT | NULL | Equipped collar item name |
| `slot_bow` | TEXT | NULL | Equipped bow item name |
| `slot_hat` | TEXT | NULL | Equipped hat item name |
| `slot_toy` | TEXT | NULL | Equipped toy item name |
| `slot_extra1` | TEXT | NULL | Unlocked at level 5 |
| `slot_extra2` | TEXT | NULL | Unlocked at level 10 |

---

### `warnings`

Moderation warning log. Not tied to internal user IDs — uses raw Discord IDs.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `user_id` | INTEGER | Discord ID of warned user |
| `guild_id` | INTEGER | Discord guild ID |
| `moderator_id` | INTEGER | Discord ID of moderating user |
| `reason` | TEXT | — |
| `timestamp` | DATETIME | Auto |

---

### `guild_config`

One row per guild. Created on first `/server set_*` use via upsert.

| Column | Type | Notes |
|---|---|---|
| `guild_id` | INTEGER PK | — |
| `prefix` | TEXT | Default `'!'` |
| `welcome_channel_id` | INTEGER | NULL = disabled |
| `welcome_message` | TEXT | Supports `{user}` and `{server}` |
| `log_channel_id` | INTEGER | NULL = no logging |
| `autorole_id` | INTEGER | NULL = disabled |
| `pet_channel_id` | INTEGER | NULL = pet DMs to owner |

---

### `action_counts`

Tracks how many times actor→target→action has occurred. Used by `/do` and `/look`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `actor_id` | INTEGER | Internal user ID |
| `target_id` | INTEGER | Internal user ID, or NULL for `/look`/everyone |
| `action` | TEXT | e.g. `'hug'`, `'blush'` |
| `count` | INTEGER | Incremented on each use |

Unique on `(actor_id, target_id, action)`. Upsert-safe.

---

### `daily_quests`

Today's shared quest pool. One row per quest per day (5 rows max per day).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | `daily_quest_id` referenced by `user_quests` |
| `quest_index` | INTEGER | Index into `QUEST_POOL` list in `utils/quests.py` |
| `date` | TEXT | ISO date string `YYYY-MM-DD` |
| `target_value` | TEXT | Daily emoji or word for emoji_use/word_use quests |

---

### `user_quests`

Per-user progress on today's quests.

| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER FK | References `users.id` |
| `daily_quest_id` | INTEGER FK | References `daily_quests.id` |
| `progress` | INTEGER | Current progress toward target |
| `completed` | INTEGER | 0 or 1 |
| `claimed` | INTEGER | 0 or 1 |
| `target_override` | INTEGER | Used for duck_clicks quests (level-scaled target) |

Primary key is `(user_id, daily_quest_id)`.

---

## `data/radio.db`

Initialized in `utils/radio/database.py` → `init_radio_db()`.

---

### `playlists`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `name` | TEXT | — |
| `owner_id` | INTEGER | Discord user ID |
| `is_public` | BOOLEAN | 0 = private |
| `source_url` | TEXT | YouTube or Spotify URL |
| `source_type` | TEXT | `'youtube'` or `'spotify'` |
| `last_synced` | TIMESTAMP | Updated on `/radio_sync` |
| `created_at` | TIMESTAMP | — |

---

### `songs`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | — |
| `playlist_id` | INTEGER FK | References `playlists.id` (CASCADE DELETE) |
| `title` | TEXT | — |
| `artist` | TEXT | — |
| `file_path` | TEXT | Local path to `.opus` file |
| `duration` | INTEGER | Seconds |
| `file_hash` | TEXT | YouTube video ID used as dedup key |
| `added_at` | TIMESTAMP | — |

---

### `user_settings`

| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER PK | Discord user ID |
| `default_volume` | REAL | 0.0–1.0, default 0.5 |
| `auto_mix` | BOOLEAN | Unused |
