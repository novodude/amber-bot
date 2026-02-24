# Amber the Discord Bot

---

## What is Amber?

Amber is a Discord bot with a growing set of fun, creative, utility, moderation, and gaming features.
The name comes from my pet duck, Amber 🦆.
New commands and systems are added regularly as the project grows.

---

## Commands

### 🎭 Fun & Reactions

| **/**                            | **description**                                                                                                                                                                           | **how I made it?**                                                                                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **`/do [action] [user]`**        | Anime action GIFs — hug, kiss, pat, poke, cuddle, bite, kick, punch, feed, highfive, dance, sleep, cry, smile, wave, laugh, yeet, baka, facepalm, think, nom, shoot, run, stare, thumbsup | Dictionary-driven actions with colors, emojis, text, and async fetching via `aiohttp` from nekos.best. |
| **`/look [reaction]`**           | Anime reaction GIFs — blush, shrug, yawn, angry, bored, happy, nope, smug, lurk, pout, nod                                                                                                | Same system as `/do`, but emotion-focused reactions.                                                   |
| **`/ping`**                      | Checks the bot's latency.                                                                                                                                                                 | Uses `bot.latency * 1000` to report milliseconds.                                                      |
| **`/rarch`**                     | Generates artistic symmetrical inkblot images.                                                                                                                                            | Pillow-based procedural generation with blur and noise.                                                |
| **`/ofc [type]`**                | Displays out-of-context images from local assets (SFW or NSFW).                                                                                                                           | Serves images locally with NSFW channel checks.                                                        |
| **`/wanted [user] [amount]`**    | Creates a wanted poster for a user.                                                                                                                                                       | Pillow image compositing with avatars and text fitting.                                                |
| **`/misquote [user] [message]`** | Generates a fake misquote image.                                                                                                                                                          | Pillow canvas with avatar and styled text.                                                             |
| **`/melody`**                    | Generates short WAV melodies from notes or beats.                                                                                                                                         | Modal input + `wavesynth` audio generation.                                                            |
| **`/8ball [question]`**          | Ask the magic 8 ball a question.                                                                                                                                                          | Random response pool.                                                                                  |
| **`/coinflip`**                  | Flip a coin.                                                                                                                                                                              | `random.choice` between heads and tails.                                                               |
| **`/no`**                        | Random rejection reasons.                                                                                                                                                                 | Fetches from `naas.isalman.dev/no` API.                                                                |
| **`/yes`**                       | Random agreement reasons.                                                                                                                                                                 | Static response pool from `assets/fun/yes.json`.                                                       |
| **`/rate [user]`**               | Rates you or another user across 6 categories.                                                                                                                                            | Random scoring with description tiers from `assets/fun/rating.json`.                                   |
| **`/download [url]`**            | Downloads audio from YouTube and uploads it to Catbox.                                                                                                                                    | Multiple fallback APIs + Catbox upload. Spotify links return metadata only.                            |

---

### 🐾 Animals

| **/**        | **description**                       |
| ------------ | ------------------------------------- |
| **`/duck`**  | Random duck GIF from `random-d.uk` 🦆 |
| **`/cat`**   | Random cat GIF from TheCatAPI 🐱      |
| **`/rotta`** | Random rat GIF from Giphy 🐀          |

---

### 💰 Economy & Profile

A simple economy and profile system powered by `aiosqlite`.
Each user has dabloons, a bio, and a customizable profile appearance.

| **/**                             | **what it does**                                            |
| --------------------------------- | ----------------------------------------------------------- |
| **`/register`**                   | Registers you in the system with 50 starter dabloons.       |
| **`/profile`**                    | Shows your profile with balance, bio, and customization UI. |
| **`/setbio [bio]`**               | Sets a text bio manually.                                   |
| **`/money balance`**              | Check your current dabloons balance.                        |
| **`/money daily`**                | Claim your daily dabloons (24h cooldown).                   |
| **`/money give [user] [amount]`** | Send dabloons to another registered user.                   |

Profile features include:

- Editable bio (modal-based, via profile buttons)
- Color theme selection (8 colors: gold, blue, red, green, purple, orange, pink, dark blue)
- Balance display
- Interactive buttons (refresh, edit bio, customize)

---

### 🎮 Games

Games integrate with the economy to reward or cost dabloons.

| **/**                                 | **description**                                                   |
| ------------------------------------- | ----------------------------------------------------------------- |
| **`/games duck_clicker`**             | Click ducks to increase your score and earn dabloons.             |
| **`/games tic_tac_toe [difficulty]`** | Play against AI — easy, medium, or hard. Costs dabloons to enter. |

**Duck Clicker:**

- Score saved per user in the database
- Only the initiating user can click
- Earn 2 dabloons every 5 clicks

**Tic Tac Toe:**

- Costs to play: `easy=2`, `medium=4`, `hard=8` dabloons
- Win rewards: `easy=4`, `medium=8`, `hard=16` dabloons
- Board updates live with button interactions

---

### 📻 Radio System

A local audio player that pulls your YouTube and Spotify playlists and syncs them locally.
Uses `yt_dlp` for downloads, `spotipy` for Spotify metadata, and `aiosqlite` for storage.

| **/**                         | **what it does**                                                                    |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| **`/radio [playlist_id]`**    | Play a saved playlist by ID. Enable `mix_mode` to shuffle all accessible playlists. |
| **`/radio_libraries`**        | List your saved playlists, or browse public ones with `public: True`.               |
| **`/radio_add [name] [url]`** | Create a new playlist from a YouTube or Spotify URL.                                |
| **`/radio_remove [id]`**      | Delete a playlist and its downloaded songs (owner only).                            |
| **`/radio_sync [id]`**        | Re-download songs from the playlist's source URL.                                   |
| **`/radio_songs [id]`**       | View all songs in a playlist (paginated, 10 per page).                              |
| **`/radio_stop`**             | Stop playback and disconnect from voice.                                            |

---

### 🛡️ Moderation

A full-featured moderation suite with logging, warnings, and server configuration.

#### Admin Commands (`/admin ...`)

| **/**                                    | **what it does**                                                          | **permission required** |
| ---------------------------------------- | ------------------------------------------------------------------------- | ----------------------- |
| **`/admin kick [member]`**               | Kick a member from the server.                                            | Kick Members            |
| **`/admin ban [member]`**                | Ban a member from the server.                                             | Ban Members             |
| **`/admin unban [user_id]`**             | Unban a user by their ID.                                                 | Ban Members             |
| **`/admin timeout [member] [duration]`** | Timeout a member (e.g. `10m`, `2h`, `1d`).                                | Moderate Members        |
| **`/admin warn [member]`**               | Warn a member and log it to the database.                                 | Kick Members            |
| **`/admin warnings [member]`**           | View all warnings for a member.                                           | Kick Members            |
| **`/admin clear_warnings [member]`**     | Clear all warnings for a member.                                          | Kick Members            |
| **`/admin purge [n]`**                   | Bulk delete up to 100 messages. Optionally filter by user.                | Manage Messages         |
| **`/admin slowmode [seconds]`**          | Set channel slowmode delay (0 to disable, max 21600).                     | Manage Channels         |
| **`/admin lockdown`**                    | Toggle lockdown on the current channel (prevents @everyone from sending). | Manage Channels         |
| **`/admin unlockdown`**                  | Lift lockdown on the current channel.                                     | Manage Channels         |

#### Server Commands (`/server ...`)

| **/**                               | **what it does**                                                      | **permission required** |
| ----------------------------------- | --------------------------------------------------------------------- | ----------------------- |
| **`/server info`**                  | Display server info — owner, members, channels, roles, creation date. | —                       |
| **`/server invite`**                | Generate a single-use 1-hour invite link.                             | —                       |
| **`/server icon`**                  | Show the server icon.                                                 | —                       |
| **`/server banner`**                | Show the server banner.                                               | —                       |
| **`/server set_prefix [prefix]`**   | Set a custom command prefix (1–5 characters).                         | Administrator           |
| **`/server set_welcome [channel]`** | Set a welcome channel and message via modal popup.                    | Administrator           |
| **`/server set_welcome_off`**       | Disable welcome messages.                                             | Administrator           |
| **`/server set_autorole [role]`**   | Auto-assign a role to every new member.                               | Administrator           |
| **`/server set_autorole_off`**      | Disable autorole.                                                     | Administrator           |
| **`/server set_log [channel]`**     | Set the channel for moderation logs.                                  | Administrator           |

**Welcome message placeholders:** `{user}` — mentions the new member · `{server}` — inserts the server name

All moderation actions are automatically logged to the configured log channel.

---

### 💬 Message Events

| trigger                | what it does                           |
| ---------------------- | -------------------------------------- |
| Reply with **`4k`**    | Quote the replied message as an image. |
| Reply with **`pin`**   | Pin the replied message.               |
| Reply with **`unpin`** | Unpin the replied message.             |

> Amber must be a member of the server for these to work.

---

## Setup

1. Clone the repository:

```bash
git clone https://github.com/novodude/amber-bot.git
cd amber-bot
```

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Get required API keys:

- Discord bot: [Discord Developer Portal](https://discord.com/developers/applications)
- Spotify API: [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Giphy API: [Giphy Developers](https://developers.giphy.com/dashboard/)
- RapidAPI (optional, for `/download`): [RapidAPI](https://rapidapi.com/)

1. Create a `.env` file:

```bash
DISCORD_TOKEN=your_bot_token
GIPHY_API=your_giphy_key
SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
RAPIDAPI_KEY=optional_key
```

1. Run the bot:

```bash
python main.py
```

---

## To-Do

- [x] Duck, cat, rat commands
- [x] Inkblot generator
- [x] Melody generator
- [x] Economy & profile system
- [x] Games system (Duck Clicker, Tic Tac Toe)
- [x] Audio downloader
- [x] Full moderation system (kick, ban, timeout, warn, purge, lockdown)
- [x] Moderation logging
- [x] Welcome messages with custom modal
- [x] Autorole system
- [x] Custom server prefix
- [ ] Gambling system
- [ ] LLM integration

---

## Dependencies

- discord.py
- aiohttp
- python-dotenv
- pillow
- wavesynth
- yt-dlp
- aiosqlite
- spotipy
- **ffmpeg** — required for audio processing in `/radio`
  > Download at [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

---

## License

MIT License — Copyright (c) 2025 Novodude and the AKO™ Team
