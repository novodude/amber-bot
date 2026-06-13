# Utils Reference

All shared utility functions and where to find them.

---

## `utils/economy.py`

Core dabloon and XP operations. All functions take **internal user ID** (`users.id`), not Discord ID.

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `add_dabloons` | `(user_id, amount)` | — | Pass negative to subtract. No balance guard. |
| `get_dabloons` | `(user_id)` | `int` | Returns 0 if user not found |
| `get_user_id_from_discord` | `(discord_id)` | `int \| None` | None if not registered |
| `get_leaderboard` | `()` | `list[tuple[str, int]]` | Top 10 `(username, balance)` |
| `add_xp` | `(user_id, amount, message)` | `int \| None` | New level if levelled up, else None. Pass `amount=None` + message string for chat XP. |
| `get_level` | `(user_id)` | `int` | — |
| `get_xp` | `(user_id)` | `int` | Current XP in current level |

---

## `utils/userbase/ensure_registered.py`

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `ensure_registered` | `(discord_id, username)` | `int` | Always returns internal user_id. Creates user + games row with 50 dabloons if not found. |

**When to use which:**

```
ensure_registered    → economy, game, pet, shop commands (invisible auto-registration)
get_user_id_from_discord → when you need to know if someone is registered (e.g. /give receiver check)
```

---

## `utils/action_counts.py`

Reaction counter helpers. These use Discord IDs, not internal IDs — they convert internally.

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `increment_action_count` | `(actor_discord_id, target_discord_id, action)` | `int` | New count. Pass `target=None` for /look. Auto-registers target. |
| `get_action_count` | `(actor_discord_id, target_discord_id, action)` | `int` | Read-only |
| `get_received_count` | `(target_discord_id, action)` | `int` | Total from all actors |
| `get_total_actions_performed` | `(actor_discord_id)` | `int` | All action types combined |
| `get_top_received_actions` | `(target_discord_id, limit=3)` | `list[tuple[str, int]]` | `[(action, count), ...]` |
| `maybe_reward_dabloons` | `(discord_id)` | `int \| None` | Award amount or None. Call after every /do or /look. |

---

## `utils/pet.py`

Pet database helpers. All take **internal user ID**.

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `get_pet` | `(user_id)` | `dict \| None` | Full pet row as dict |
| `create_pet` | `(user_id, name)` | `dict` | Inserts + returns pet |
| `update_pet` | `(user_id, **kwargs)` | — | Updates any columns by keyword |
| `add_pet_xp` | `(user_id, amount)` | `int \| None` | New level if levelled up |
| `feed_pet` | `(user_id, effect)` | `tuple[int, int]` | `(new_hunger, new_happiness)` |
| `equip_accessory` | `(user_id, slot, item_name)` | `bool` | False if slot locked |
| `touch_owner_activity` | `(user_id)` | — | Updates `last_owner_activity` timestamp |
| `apply_decay` | `(hunger, happiness, last_fed, last_played)` | `tuple[int, int]` | Pure function, no DB |
| `get_unlocked_slots` | `(level)` | `list[str]` | Slot column names unlocked at this level |
| `get_toy_style` | `(toy)` | `str` | `"zoomies"`, `"hunt"`, `"happy"`, or `"default"` |
| `get_hat_emoji` | `(hat)` | `str` | Hat emoji or empty string |
| `xp_to_next_level` | `(level)` | `int` | XP threshold formula |

---

## `utils/cat_model.py`

Cat message generation. Uses LLM if available, synthesis engine otherwise.

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `build_check_in_message` | `(pet_name, happiness, hunger, toy_style, owner_context?)` | `str` | Full formatted message: `"**Name:** ..."`. Main entrypoint. |
| `generate_cat_message` | `(instruction, context, temperature?, max_new_tokens?)` | `str` | Lower-level. LLM or synthesis. |
| `pick_style` | `(happiness, hunger, toy_style)` | `str` | Selects style key based on pet state |

Style keys: `food`, `play`, `sleep`, `affection`, `grooming`, `alarm`, `boredom`, `comfort`, `zoomies`, `hunt`, `happy`

---

## `utils/banking.py`

Profile embed builder and interactive views.

| Function / Class | Notes |
|---|---|
| `build_profile_embed(discord_id, user, balance, bio, color, greeting_time)` | Async. Returns full profile `Embed` with action stats |
| `ProfileView(discord_id)` | Interactive profile view. Buttons: Refresh, Edit Bio, Customize |
| `ProfileView.get_color(color_name)` | Returns `discord.Color` from color name string |
| `BioEditView(user_id, profile_view)` | Shown when Edit Bio is clicked. Buttons: edit bio, clear bio, back |
| `SetBioModal(profile_view)` | Modal for bio text input |
| `ColorSelect(profile_view)` | Select dropdown for 8 base profile colors |

---

## `utils/reactions.py`

Reaction data and embed builders.

| Function / Object | Notes |
|---|---|
| `ACTIONS` | Dict of all `/do` action definitions |
| `REACTION` | Dict of all `/look` reaction definitions |
| `ACTION_PAST_TENSE` | Action → past-tense verb mapping |
| `PRIVATE_COUNTER_ACTIONS` | Set of actions using private counter format (currently `{'kiss'}`) |
| `build_title(action, action_data, author_name, target_name, everyone, react_back)` | Builds embed title string |
| `build_counter_text(action, count, author_name, target_name, is_look)` | Builds `-#` counter line |
| `build_embed(color, title, description, action, author)` | Async. Fetches GIF + builds Embed |
| `get_gif_url(action)` | Async. Fetches from nekos.best |
| `button_text(action, action_data)` | Returns react-back button label |
| `React_back(author, user, action, show_button)` | View with react-back button |

---

## `utils/quests.py`

Quest pool and progress tracking.

| Function | Signature | Notes |
|---|---|---|
| `get_or_create_daily_quests()` | `()` | Returns today's 5 quest rows, creating them if needed |
| `get_user_daily_quests(discord_id)` | `(discord_id)` | User's slice of today's quests with progress |
| `increment_quest_progress(discord_id, quest_type, amount=1)` | `(discord_id, type, amount)` | Called by games and message handler |
| `claim_quest(discord_id, daily_quest_id)` | `(discord_id, id)` | Returns `(success, message, dabloons, xp)` |
| `message_quest_handler(message)` | `(message)` | Call from `on_message` — tracks emoji/word quests |
| `get_daily_targets()` | `()` | Returns `(daily_emoji, daily_word)` for today |
| `calculate_duck_target(level, tier)` | `(level, tier)` | Computes duck click target for a level |
| `get_quest_count_for_level(level)` | `(level)` | Returns 3, 4, or 5 |

---

## `utils/userbase/database.py`

| Function | Notes |
|---|---|
| `init_user_db()` | Creates all user.db tables if not exist. Seeds shop. Runs migrations. Call once in `on_ready`. |

Also exports `DB_PATH = "data/user.db"` — import this instead of hardcoding the path.

---

## `utils/radio/database.py`

| Function | Notes |
|---|---|
| `init_radio_db()` | Creates radio.db tables. Call once in `on_ready`. |

Also exports `DB_PATH = "data/radio.db"`.

---

## `utils/radio/audio_processor.py`

| Function | Returns | Notes |
|---|---|---|
| `download_from_youtube(url, playlist_id)` | `(bool, list, str \| None)` | `(success, added_titles, warning_message)` |
| `download_from_spotify(url, playlist_id)` | `(bool, list, str \| None)` | Delegates to YouTube per track |
| `convert_to_opus(input_path, output_path)` | — | FFmpeg subprocess, sync |
