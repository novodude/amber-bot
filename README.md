# Amber the Discord Bot

---

## What is Amber?

Amber is a Discord bot with a growing set of fun, creative, utility, moderation, and gaming features.
The name comes from my pet duck, Amber 🦆.
New commands and systems are added regularly as the project grows.

[click here to add the bot to your server](https://discord.com/oauth2/authorize?client_id=1432674707970457703&permissions=8&integration_type=0&scope=bot)

---

## Commands

### General

| **/**                            | **description**                                                                                                                                                                     | **how I made it?**                                                                                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **`/do [action] [user]`**        | Anime action GIFs — hug, kiss, pat, poke, cuddle, bite, kick, punch, feed, highfive, dance, sleep, cry, smile, wave, laugh, yeet, baka, facepalm, peck, shoot, run, stare, thumbsup | Dictionary-driven actions with colors, emojis, text, and async fetching via `aiohttp` from nekos.best. |
| **`/look [reaction]`**           | Anime reaction GIFs — blush, shrug, yawn, angry, bored, happy, nope, smug, lurk, pout, nod                                                                                          | Same system as `/do`, but emotion-focused reactions.                                                   |
| **`/ping`**                      | Checks the bot's latency.                                                                                                                                                           | Uses `bot.latency * 1000` to report milliseconds.                                                      |
| **`/rarch`**                     | Generates artistic symmetrical inkblot images.                                                                                                                                      | Pillow-based procedural generation with blur and noise.                                                |
| **`/ofc [type]`**                | Displays out-of-context images from local assets (SFW or NSFW).                                                                                                                     | Serves images locally with NSFW channel checks.                                                        |
| **`/wanted [user] [amount]`**    | Creates a wanted poster for a user.                                                                                                                                                 | Pillow image compositing with avatars and text fitting.                                                |
| **`/misquote [user] [message]`** | Generates a fake misquote image.                                                                                                                                                    | Pillow canvas with avatar and styled text.                                                             |
| **`/melody`**                    | Generates short WAV melodies from notes or beats.                                                                                                                                   | Modal input + `wavesynth` audio generation.                                                            |
| **`/8ball [question]`**          | Ask the magic 8 ball a question.                                                                                                                                                    | Random response pool.                                                                                  |
| **`/coinflip`**                  | Flip a coin.                                                                                                                                                                        | `random.choice` between heads and tails.                                                               |
| **`/no`**                        | Random rejection reasons.                                                                                                                                                           | Fetches from `naas.isalman.dev/no` API.                                                                |
| **`/yes`**                       | Random agreement reasons.                                                                                                                                                           | Static response pool from `assets/fun/yes.json`.                                                       |
| **`/rate [user]`**               | Rates you or another user across 6 categories.                                                                                                                                      | Random scoring with description tiers from `assets/fun/rating.json`.                                   |
| **`/download [url]`**            | Downloads audio from a YouTube (or supported) URL using yt‑dlp and sends the file directly to Discord.                                                                              | Simplified implementation – no RapidAPI key required.                                                  |
| **`/mimic start [@user]`**       | Makes Amber repeat the target user's messages, with a 30% chance of sending one of their last 15 messages instead.                                                                  | Admin only. Mirrors text, attachments, and stickers.                                                   |
| **`/say embed [message]`**       | Makes Amber send an embed message.                                                                                                                                                  | Supports text, timestamps, author display, image attachments, and 6 color options.                     |
| **`/say text [message]`**        | Makes Amber say a text message.                                                                                                                                                     | Can send text and attachments.                                                                         |

---

### 👤 User & Profile Utilities

Commands for looking up user info and viewing your own action stats.

| **/**                     | **description**                                                                          |
| ------------------------- | ---------------------------------------------------------------------------------------- |
| **`/user info [user]`**   | Get a user's username, ID, and account creation date.                                    |
| **`/user avatar [user]`** | Display a user's avatar.                                                                 |
| **`/user banner [user]`** | Display a user's banner (if they have one).                                              |
| **`/my stats [type]`**    | View your action stats — how many actions you've given or received, broken down by type. |

**Implementation notes:**

- `/user` commands work in guilds, DMs, and private channels
- `/my stats` uses a dropdown to switch between Actions Given and Actions Received without re-running the command
- Stats pull from the same counter system that tracks `/do` and `/look` interactions

---

### 🌸 Anime

A unified `/anime` command group for anime images and quotes. Images are fetched from [nekos.best](https://nekos.best) and quotes from [yurippe](https://yurippe.vercel.app).

| **/**                 | **what it does**                   |
| --------------------- | ---------------------------------- |
| **`/anime waifu`**    | Get a random anime waifu image.    |
| **`/anime husbando`** | Get a random anime husbando image. |
| **`/anime neko`**     | Get a random anime neko image.     |
| **`/anime kitsune`**  | Get a random anime kitsune image.  |
| **`/anime quote`**    | Get a random anime quote.          |

**Implementation notes:**

- Images fetched from `nekos.best/api/v2` — returns artist name, artist href, source URL, and dimensions
- Quotes fetched from `yurippe.vercel.app/api/quotes` — no auth, no rate limit
- Each image embed includes artist credit and a link to the original artwork
- Quote embed displays the quote text, character name, and anime title

---

### 🖼️ Image Commands

A unified `/image` command group for manipulating images. Accepts both uploaded attachments and direct URLs. Powered by Pillow.

| **/**                                      | **what it does**                                      |
| ------------------------------------------ | ----------------------------------------------------- |
| **`/image wanted [user] [amount]`**        | Create a wanted poster for a user.                    |
| **`/image misquote [user] [message]`**     | Generate a fake quote image.                          |
| **`/image rarch`**                         | Generate a random Rorschach inkblot image.            |
| **`/image caption [caption] [image/url]`** | Add a caption above an image.                         |
| **`/image meme [caption] [image/url]`**    | Add a meme-style caption to an image (top or bottom). |
| **`/image grayscale [image/url]`**         | Convert an image to grayscale.                        |
| **`/image blur [image/url]`**              | Apply a blur effect.                                  |
| **`/image rotate [angle] [image/url]`**    | Rotate an image — 90°, 180°, or 360°.                 |
| **`/image flip [axis] [image/url]`**       | Flip an image horizontally, vertically, or both.      |
| **`/image invert [image/url]`**            | Invert the colors of an image.                        |
| **`/image pixelate [image/url]`**          | Pixelate an image.                                    |
| **`/image deepfry [image/url]`**           | Apply a deep fry effect.                              |
| **`/image edgedetect [image/url]`**        | Apply an edge detection filter.                       |
| **`/image rainbow [image/url]`**           | Overlay a rainbow gradient.                           |
| **`/image sepia [image/url]`**             | Apply a sepia tone.                                   |
| **`/image emboss [image/url]`**            | Apply an emboss effect.                               |
| **`/image solarize [image/url]`**          | Apply a solarize effect.                              |
| **`/image posterize [image/url]`**         | Apply a posterize effect.                             |
| **`/image glitch [image/url]`**            | Apply a glitch effect.                                |
| **`/image swirl [image/url]`**             | Apply a swirl/warp effect.                            |

**Implementation notes:**

- All filter commands accept either a file attachment or a `url` string — both optional, one required
- Alpha channel is preserved correctly across all filters
- Built with Pillow — filters include custom implementations of deepfry, glitch, swirl, sepia, and posterize

---

### 🐾 Animals

A unified `/animal` command group with multiple subcommands for different animals. Uses multiple APIs (random-d.uk, TheCatAPI, TheDogAPI, some-random-api, etc.) with async fetching and embed responses.

| **/**                  | **description**                       |
| ---------------------- | ------------------------------------- |
| **`/animal duck`**     | Random duck GIF from `random-d.uk` 🦆 |
| **`/animal cat`**      | Random cat GIF + fact 🐱              |
| **`/animal dog`**      | Random dog GIF 🐶                     |
| **`/animal rotta`**    | Random rat GIF from Giphy 🐀          |
| **`/animal fox`**      | Random fox image 🦊                   |
| **`/animal bird`**     | Random bird image + fact 🐦           |
| **`/animal panda`**    | Random panda image + fact 🐼          |
| **`/animal redpanda`** | Random red panda image + fact 🦊      |
| **`/animal koala`**    | Random koala image + fact 🐨          |
| **`/animal kangaroo`** | Random kangaroo image + fact 🦘       |
| **`/animal bunny`**    | Random bunny image/GIF 🐰             |
| **`/animal sheep`**    | Random sheep GIF 🐑                   |

**Implementation notes:**

- Centralized helper methods for sending embeds and handling errors
- Multiple API integrations
- Uses `aiohttp` for async requests
- Works in guilds and DMs

---

### 💰 Economy & Profile

A simple economy and profile system powered by `aiosqlite`.
Each user has dabloons, a bio, and a customizable profile appearance.

| **/**                             | **what it does**                                                                                                    |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **`/register`**                   | Registers you in the system with 50 starter dabloons.                                                               |
| **`/profile`**                    | Shows your profile with balance, bio, and customization UI.                                                         |
| **`/setbio [bio]`**               | Sets a text bio manually.                                                                                           |
| **`/money balance`**              | Check your current dabloons balance.                                                                                |
| **`/money daily`**                | Claim your daily dabloons (24h cooldown).                                                                           |
| **`/money give [user] [amount]`** | Send dabloons to another registered user.                                                                           |
| **`/money leaderboard`**          | Show the top 10 users globally by balance.                                                                          |
| **`/money rob [user]`**           | Attempt to steal dabloons from another user. Success is a 50/50 shot; failure results in a fine paid to the victim. |
| **`/money beg`**                  | Ask for dabloons with varying levels of success based on luck.                                                      |

Profile features include:

- Editable bio (modal-based, via profile buttons)
- Color theme selection — 8 default colors plus unlockable shop themes (cyan, rose, midnight) and full custom hex color support
- Balance and action stats display
- Interactive buttons (refresh, edit bio, customize)

---

### 🛒 Shop

A full item shop where you spend dabloons on upgrades, pet supplies, and cosmetics.

| **/**                   | **what it does**                                          |
| ----------------------- | --------------------------------------------------------- |
| **`/shop browse`**      | Browse all shop categories with a dropdown selector.      |
| **`/shop buy [item]`**  | Purchase an item by name.                                 |
| **`/shop inventory`**   | View consumables and accessories you currently own.       |
| **`/shop mypurchases`** | View your permanent unlocks (colors, game upgrades, etc.) |

**Categories:**

| Category          | Items                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------- |
| 🎮 Games          | Auto Clicker, Double Points, Custom X/O symbols for Tic Tac Toe                       |
| 🍖 Pet Food       | Kibble, Tuna Can, Fancy Feast, Treat Bag                                              |
| 🎀 Accessories    | Collars (XP boost), Bows (dabloon boost), Hats (cosmetic), Toys (affect pet messages) |
| 🍬 Pet Candy      | XP Candy, Rare Candy, Mega Candy — level up your pet fast                             |
| 🎨 Profile Colors | Cyan, Rose, Midnight themes + Custom hex color unlock                                 |

**Game upgrades:**

- **Auto Clicker** — clicks Duck Clicker for you every 60 seconds in the background, even while you're offline. Dabloon rewards and quest progress are tracked automatically.
- **Double Points** — earn 4 dabloons per 5 clicks instead of 2, works with the Auto Clicker too.
- **Custom X/O Symbols** — replace ❌ with ⭐ and ⭕ with 💫 in Tic Tac Toe.

---

### 🐱 Pet System

Adopt a cat companion powered by **domesticated-LLM** — a fine-tuned 135M language model trained to speak in cat noises, broken words, and chaotic emotes.

| **/**                          | **what it does**                                                         |
| ------------------------------ | ------------------------------------------------------------------------ |
| **`/pet adopt [name]`**        | Adopt your cat and give it a name.                                       |
| **`/pet status`**              | Check your cat's hunger, happiness, level, XP, and equipped accessories. |
| **`/pet feed [item]`**         | Feed your cat using food from your inventory.                            |
| **`/pet play`**                | Play with your cat to boost happiness and earn pet XP (1h cooldown).     |
| **`/pet candy [item]`**        | Use candy to give your pet a direct XP boost.                            |
| **`/pet equip [slot] [item]`** | Equip an accessory to a slot (collar, bow, hat, toy, extra1, extra2).    |
| **`/pet unequip [slot]`**      | Remove the item from a slot.                                             |
| **`/pet rename [name]`**       | Give your cat a new name.                                                |

---

### 🎮 Games

Games integrate with the economy to reward or cost dabloons.

| **/**                                 | **description**                                                   |
| ------------------------------------- | ----------------------------------------------------------------- |
| **`/games duck_clicker`**             | Click ducks to increase your score and earn dabloons.             |
| **`/games tic_tac_toe [difficulty]`** | Play against AI — easy, medium, or hard. Costs dabloons to enter. |
| **`/games trivia`**                   | Answer a trivia question from a random category and difficulty.   |

---

### 📻 Radio System

A streaming radio player that pulls tracks from YouTube and Spotify playlists and plays them directly — **nothing is saved to disk**.
Uses `yt-dlp` for stream resolution, `spotipy` for Spotify metadata, and `aiosqlite` for playlist storage.
All commands live under the `/radio` group.

| **/**                                                   | **what it does**                                                                                                                       |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **`/radio play [playlist_id] [source_url] [mix_mode]`** | Play a saved playlist by ID, stream a single YouTube URL directly, or shuffle all accessible playlists with mix mode.                  |
| **`/radio queue [source_url]`**                         | Add a YouTube URL to the end of the current queue without interrupting playback.                                                       |
| **`/radio add [name] [url] [public]`**                  | Create a new playlist from a YouTube or Spotify URL. Syncs in the background with a live progress bar — up to 1500 songs per playlist. |
| **`/radio sync [playlist_id]`**                         | Re-sync a playlist from its source URL. Runs in the background with a progress bar.                                                    |
| **`/radio libraries [public]`**                         | List your saved playlists, or browse public ones with `public: True`.                                                                  |
| **`/radio remove [playlist_id]`**                       | Delete a playlist and all its song entries (owner only).                                                                               |
| **`/radio songs [playlist_id]`**                        | View all songs in a playlist (paginated, 10 per page).                                                                                 |
| **`/radio stop`**                                       | Stop playback and disconnect from voice.                                                                                               |

**How syncing works:**

- `/radio add` and `/radio sync` respond immediately, then run in the background
- A live embed updates every 5 songs with a progress bar and the last added track name
- You get a DM when the sync finishes
- Playlist cap is **1500 songs** per playlist

---

### 🎲 Gambling

A high-stakes command group for the bold.

| **/**                                 | **description**                                                                  |
| :------------------------------------ | :------------------------------------------------------------------------------- |
| **`/gamble coinflip [bet] [choice]`** | Bet on heads or tails to double your money.                                      |
| **`/gamble roll [bet] [choice]`**     | Bet on a specific dice face (1-6) for a **5x** payout.                           |
| **`/gamble slots [bet]`**             | Spin for a **2x** payout (two of a kind) or a **10x** Jackpot (three of a kind). |

---

### 📋 Daily Quests

A dynamic daily quest system that encourages interaction across the bot's features.
Quests refresh every day and scale with your level.

| **/**         | **what it does**                           |
| ------------- | ------------------------------------------ |
| **`/quests`** | View your current daily quests.            |
| **`/level`**  | View your level and needed XP to level up. |

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

| **/**                                  | **what it does**                                                      | **permission required** |
| -------------------------------------- | --------------------------------------------------------------------- | ----------------------- |
| **`/server info`**                     | Display server info — owner, members, channels, roles, creation date. | —                       |
| **`/server invite`**                   | Generate a single-use 1-hour invite link.                             | —                       |
| **`/server icon`**                     | Show the server icon.                                                 | —                       |
| **`/server banner`**                   | Show the server banner.                                               | —                       |
| **`/server set_prefix [prefix]`**      | Set a custom command prefix (1–5 characters).                         | Administrator           |
| **`/server set_welcome [channel]`**    | Set a welcome channel and message via modal popup.                    | Administrator           |
| **`/server set_welcome_off`**          | Disable welcome messages.                                             | Administrator           |
| **`/server set_autorole [role]`**      | Auto-assign a role to every new member.                               | Administrator           |
| **`/server set_autorole_off`**         | Disable autorole.                                                     | Administrator           |
| **`/server set_log [channel]`**        | Set the channel for moderation logs.                                  | Administrator           |
| **`/server set_4k_channel [channel]`** | Set a channel where 4k image results are forwarded automatically.     | Manage Channels         |
| **`/server set_4k_channel_off`**       | Disable 4k channel forwarding.                                        | Manage Channels         |

---

### 💬 Message Events

| trigger                | what it does                                                                              |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Reply with **`4k`**    | Quote the replied message as an image. Also forwards to the configured 4k channel if set. |
| Reply with **`pin`**   | Pin the replied message.                                                                  |
| Reply with **`unpin`** | Unpin the replied message.                                                                |

---

## Setup

The easiest way to get started is with `amber.py` — it handles everything automatically.

```bash
git clone https://github.com/novodude/amber-bot.git
cd amber-bot
python amber.py
```

`amber.py` will:

1. Pull the latest changes from GitHub
2. Create and activate a virtual environment
3. Install all dependencies
4. Download the `domesticated-LLM` model from HuggingFace
5. Check that all required files are present
6. Prompt you for API keys and save them to `.env`
7. Launch the bot

To update at any time, run:

```bash
python update.py
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
- [x] Shop system with upgrades, food, accessories, colors
- [x] Pet system — cat companion powered by domesticated-LLM
- [x] LLM integration (domesticated-LLM — cat-speak fine-tune of SmolLM2-135M)
- [x] Auto setup script (amber.py) and updater (update.py)
- [x] Anime commands — waifu, husbando, neko, kitsune, quote
- [x] Shop upgrades fully implemented (Auto Clicker, Double Points, Custom X/O)
- [x] 4k channel forwarding
- [x] Streaming radio — no disk usage, up to 1500 songs/playlist, background sync with live progress bar
- [x] Gambling system
- [x] User info, avatar, and banner commands
- [x] Action stats command (`/my stats`)

---

## The Model — domesticated-LLM

The pet system uses **domesticated-LLM**, a fine-tuned version of `SmolLM2-135M-Instruct` trained on 20,000 synthetic cat-speak examples across 8 behavior styles (food, play, sleep, affection, grooming, alarm, boredom, comfort).

Full model card: [novodude/domesticated-LLM](https://huggingface.co/novodude/domesticated-LLM)

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
- torch
- transformers
- accelerate
- **ffmpeg** — required for audio streaming in `/radio`
  > Download at [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

---

## License

MIT License — Copyright (c) 2025 Novodude and the AKO™ Team
