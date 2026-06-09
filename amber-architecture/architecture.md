# Architecture

How the codebase is organized and how the pieces connect.

---

## File Tree

```
amber-bot/
├── main.py                        # bot startup, event listeners, command registration
├── amber.py                       # guided setup & launcher (run this first)
├── update.py                      # git pull + dependency updater
│
├── commands/
│   ├── animals.py                 # /animal command group (Cog-style Group)
│   ├── banking.py                 # /money, /profile, /setbio, /level
│   ├── fun.py                     # /8ball, /coinflip, /ofc, /rate, /no, /yes
│   ├── helper.py                  # /help command + search system + COMMANDS dict
│   ├── image.py                   # /image command group + ImageGenerator class
│   ├── melody.py                  # /melody command + wavesynth audio generation
│   ├── mimic.py                   # /mimic commands (Cog)
│   ├── minigames.py               # /games duck_clicker, /games tic_tac_toe, /games trivia
│   ├── moderation.py              # /admin, /server commands (Cog)
│   ├── pet.py                     # /pet commands (Cog + background task)
│   ├── quests.py                  # /quests command (Cog)
│   ├── reactions.py               # /do and /look commands
│   ├── shop.py                    # /shop commands (Cog)
│   ├── utils.py                   # /say, /download, pin/unpin helpers
│   └── radio/
│       ├── __init__.py
│       ├── player.py              # /radio, /radio_stop (Cog)
│       └── settings.py            # /radio_add, /radio_sync, /radio_remove, /radio_libraries, /radio_songs (Cog)
│
├── utils/
│   ├── action_counts.py           # reaction counters + dabloon reward helper
│   ├── banking.py                 # ProfileView, ColorSelect, build_profile_embed
│   ├── cat_model.py               # LLM + synthesis engine for cat messages
│   ├── economy.py                 # add_dabloons, get_dabloons, XP helpers, leaderboard
│   ├── pet.py                     # DB helpers for pet table + decay logic
│   ├── quests.py                  # quest pool, daily generation, progress tracking
│   ├── reactions.py               # ACTIONS dict, REACTION dict, embed builder, GIF fetcher
│   ├── radio/
│   │   ├── __init__.py
│   │   ├── audio_processor.py     # yt-dlp download, Spotify metadata, ffmpeg conversion
│   │   └── database.py            # init_radio_db()
│   └── userbase/
│       ├── __init__.py
│       ├── database.py            # init_user_db() — all table creation + shop seed
│       └── ensure_registered.py   # ensure_registered() — silent auto-registration
│
├── assets/
│   ├── fonts/                     # TTF fonts for image commands
│   ├── fun/                       # wanted.png template, rating.json, yes.json
│   └── ofc/                       # sfw/ and nsfw/ out-of-context images
│
└── data/                          # gitignored — created at runtime
    ├── user.db
    ├── radio.db
    └── audio/                     # downloaded playlist audio files
```

---

## Two Patterns: setup functions vs Cogs

Commands are registered in two styles depending on complexity.

**Setup functions** — used for most commands. A bare `async def <name>_setup(bot)` that registers commands directly on `bot.tree`. No persistent state.

```python
async def fun_setup(bot):
    @bot.tree.command(name="coinflip", ...)
    async def coinflip(interaction):
        ...
```

**Cogs** — used when the command group needs shared state, background tasks, or many subcommands. Loaded via `bot.load_extension(...)` or `bot.add_cog(...)`.

```python
class ModerationCog(commands.Cog):
    ...

async def moderation_setup(bot):
    await bot.add_cog(ModerationCog(bot))
```

**Which files use which:**

| File | Pattern |
|---|---|
| `reactions.py` | setup function |
| `fun.py` | setup function |
| `banking.py` | setup function |
| `melody.py` | setup function |
| `utils.py` | setup function |
| `helper.py` | setup function |
| `animals.py` | `app_commands.Group` class + setup function |
| `image.py` | `app_commands.Group` class + setup function |
| `minigames.py` | `app_commands.Group` class + setup function |
| `moderation.py` | Cog (loaded via `add_cog`) |
| `mimic.py` | Cog (loaded via `add_cog`) |
| `pet.py` | Cog with background task (loaded via `add_cog`) |
| `shop.py` | Cog (loaded via `add_cog`) |
| `quests.py` | Cog (loaded via `load_extension`) |
| `radio/player.py` | Cog (loaded via `load_extension`) |
| `radio/settings.py` | Cog (loaded via `load_extension`) |

---

## Event Flow: `on_message`

Every non-bot message passes through this pipeline in `main.py`:

```
on_message(message)
  ├── handle_4k()            ← "4k" reply → quote image
  ├── handle_pin()           ← "pin"/"unpin" reply → pin the message
  ├── message_xp_handler()   ← award XP for chatting, level-up notification
  ├── message_quest_handler() ← track emoji_use and word_use quest progress
  ├── touch_owner_activity() ← reset pet inactivity timer
  ├── mimic_cog.handle_mimic() ← mirror target users if active
  └── bot.process_commands() ← handle prefix commands (legacy)
```

---

## Two Databases

### `data/user.db`

Everything player-facing. Initialized by `utils/userbase/database.py`.

Tables: `users`, `games`, `inventory`, `shop`, `user_purchases`, `pets`, `warnings`, `guild_config`, `action_counts`, `daily_quests`, `user_quests`

### `data/radio.db`

Radio playlists and downloaded songs. Initialized by `utils/radio/database.py`.

Tables: `playlists`, `songs`, `user_settings`

---

## ID Conventions

Discord IDs and internal DB IDs are different. Always be explicit about which you have.

| Variable name | Meaning |
|---|---|
| `discord_id` | The raw Discord snowflake (`interaction.user.id`) |
| `user_id` | The internal auto-increment `users.id` from the DB |

Use `get_user_id_from_discord(discord_id)` to convert. Use `ensure_registered(discord_id, username)` when you want auto-registration.
