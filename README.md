# Amber the Discord Bot

---

## What is Amber?

Amber is a Discord bot with a growing set of fun, creative, utility, and gaming features.
The name comes from my pet duck, Amber 🦆.
New commands and systems are added regularly as the project grows.

---

## Commands

| **/**           | **description**                                                                 | **how I made it?**                                                                     |
| --------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **`/do`**       | Anime action images (hug, slap, laugh, etc.) using random GIFs from nekos.best. | Dictionary-driven actions with colors, emojis, text, and async fetching via `aiohttp`. |
| **`/look`**     | Anime reaction images (happy, blush, angry, etc.).                              | Same system as `/do`, but emotion-focused reactions.                                   |
| **`/ping`**     | Checks the bot's latency.                                                       | Uses `bot.latency * 1000` to report milliseconds.                                      |
| **`/duck`**     | Fetches a random duck GIF.                                                      | Pulls a random file from `random-d.uk` API.                                            |
| **`/cat`**      | Fetches a random cat image.                                                     | Uses TheCatAPI and embeds the result.                                                  |
| **`/rat`**      | Fetches a random rat GIF.                                                       | Uses Giphy random endpoint with `GIPHY_API`.                                           |
| **`/rarch`**    | Generates artistic symmetrical inkblot images.                                  | Pillow-based procedural generation with blur and noise.                                |
| **`/ofc`**      | Displays out-of-context images from local assets.                               | Serves images locally with NSFW checks.                                                |
| **`/wanted`**   | Creates a wanted poster for a user.                                             | Pillow image compositing with avatars and text fitting.                                |
| **`/misquote`** | Generates a fake misquote image.                                                | Pillow canvas with avatar and styled text.                                             |
| **`/melody`**   | Generates short WAV melodies from notes or beats.                               | Modal input + `wavesynth` audio generation.                                            |
| **`/no`**       | Random rejection reasons.                                                       | Static response pool.                                                                  |
| **`/yes`**      | Random agreement reasons.                                                       | Static response pool.                                                                  |
| **`/rate`**     | Rates you or another user.                                                      | Simple scoring logic with embeds.                                                      |
| **`/download`** | Downloads audio from YouTube links and uploads it.                              | Multiple fallback APIs + Catbox upload, Spotify links supported for metadata only.     |

---

## Banking & Profile System

A simple economy and profile system powered by `aiosqlite`.
Each user has dabloons, a bio, and a customizable profile appearance.

| **/**           | **what it does**                                            |
| --------------- | ----------------------------------------------------------- |
| **`/register`** | Registers you in the system with starter dabloons.          |
| **`/profile`**  | Shows your profile with balance, bio, and customization UI. |
| **`/setbio`**   | Sets a text bio manually.                                   |
| **`/balance`**  | Check your current dabloons balance.                        |
| **`/daily`**    | Claim your daily dabloons.                                  |
| **`/give`**     | Send dabloons to another registered user.                   |

Profile features include:

- Editable bio (modal-based)
- Color theme selection
- Balance display
- Interactive buttons (refresh, customize, edit)

---

## Games System

Games now integrate with the economy to reward or cost dabloons.

| **/**               | **description**                                   |
| ------------------- | ------------------------------------------------- |
| **`/duck_clicker`** | Click ducks to increase score and earn dabloons.  |
| **`/tic_tac_toe`**  | Play against AI with difficulty levels and costs. |

**Duck Clicker features:**

- Score saved per user in DB
- Only the initiating user can click
- Earn 2 dabloons every 5 clicks

**Tic Tac Toe features:**

- Costs dabloons to play (`easy=2`, `medium=4`, `hard=8`)
- AI difficulty scaling (`easy`, `medium`, `hard`)
- Win rewards: `easy=4`, `medium=8`, `hard=16`
- Board updates live with button interactions

---

## Radio System

A local audio player that pulls your YouTube and Spotify\* playlists
and syncs them locally to play later.

It uses:

- `yt_dlp` to download audio
- `spotipy` for Spotify metadata
- `aiosqlite` for playlist storage

| **/**                  | **what it does**              |
| ---------------------- | ----------------------------- |
| **`/radio`**           | Play a saved playlist by ID.  |
| **`/radio_libraries`** | List saved playlists.         |
| **`/radio_add`**       | Add a new playlist.           |
| **`/radio_remove`**    | Remove a playlist by ID.      |
| **`/radio_stop`**      | Stop playback and disconnect. |
| **`/radio_sync`**      | Sync playlists from a link.   |
| **`/radio_songs`**     | Show songs in a playlist.     |

---

## Message Events

| trigger     | what it does                                     |
| ----------- | ------------------------------------------------ |
| **`4k`**    | Reply with `4k` to quote the referenced message. |
| **`pin`**   | Reply with `pin` to pin a message.               |
| **`unpin`** | Reply with `unpin` to unpin a message.           |

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

- Spotify API: [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Giphy API: [Giphy Developers](https://developers.giphy.com/dashboard/)
- [RapidAPI](https://rapidapi.com/) (optional, for `/download`)

1. Create a `.env` file:

```bash
TOKEN=your_bot_token
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
- [x] Banking & profile system
- [x] Games system (Duck Clicker, Tic Tac Toe)
- [x] Audio downloader
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
- **ffmpeg**:
  required for audio processing in some commands (like /radio)

  > visit [FFmpeg download page](https://ffmpeg.org/download.html)

---

## License

MIT License

Copyright (c) 2025 Novodude
