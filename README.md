# Amber the Discord Bot

---

## What is Amber?

Amber is a Discord bot with a growing set of fun, creative, utility, moderation, and gaming features.
The name comes from my pet duck, Amber 🦆.
New commands and systems are added regularly as the project grows.

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
| **`/download [url]`**            | Downloads audio from YouTube and uploads it to Catbox.                                                                                                                              | Multiple fallback APIs + Catbox upload. Spotify links return metadata only.                            |
| **`/mimic start [@user]`**       | Makes Amber repeat the target user's messages, with a 30% chance of sending one of their last 15 messages instead.                                                                  | Admin only. Mirrors text, attachments, and stickers.                                                   |
| **`/say embed [message]`**       | Makes Amber send an embed message.                                                                                                                                                  | Supports text, timestamps, author display, image attachments, and 6 color options.                     |
| **`/say text [message]`**        | Makes Amber say a text message.                                                                                                                                                     | Can send text and attachments.                                                                         |

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

**Implementation notes:**

- Centralized helper methods for sending embeds and handling errors
- Multiple API integrations
- Uses `aiohttp` for async requests
- Works in guilds and DMs

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
| **`/money leaderboard`**          | Show the top 10 users globally by balance.                  |

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

**How it works:**

- Your cat has **hunger** and **happiness** stats that decay over time
- Hunger drops 5 points per hour. Happiness drops if hunger falls below 30
- Feed and play with your cat to keep it happy
- Happy cats generate more playful and varied messages
- Your cat will **message you or your server's pet channel** when you've been inactive for 4+ hours — it checks on you using the AI model, responding based on its current mood, hunger, and equipped toy
- The cat won't spam — there's a 6h cooldown between check-in messages per owner

**Accessories & effects:**

| Slot    | Effect                                                                                               |
| ------- | ---------------------------------------------------------------------------------------------------- |
| Collar  | XP boost — Red Collar +10%, Gold Collar +25%                                                         |
| Bow     | Dabloon drop boost — Silk Bow +10%, Diamond Bow +25%                                                 |
| Hat     | Cosmetic — shown as an emoji on `/pet status`                                                        |
| Toy     | Changes the cat's message style — Yarn Ball (happy), Laser Pointer (zoomies), Feather Wand (hunting) |
| Extra 1 | Unlocks at level 5                                                                                   |
| Extra 2 | Unlocks at level 10                                                                                  |

**Pet leveling:**

- Pet gains XP from playing and eating candy
- Leveling up unlocks new accessory slots
- Use Mega Candy for big XP jumps

---

### 🎮 Games

Games integrate with the economy to reward or cost dabloons.

| **/**                                 | **description**                                                   |
| ------------------------------------- | ----------------------------------------------------------------- |
| **`/games duck_clicker`**             | Click ducks to increase your score and earn dabloons.             |
| **`/games tic_tac_toe [difficulty]`** | Play against AI — easy, medium, or hard. Costs dabloons to enter. |
| **`/games trivia`**                   | Answer a trivia question from a random category and difficulty.   |

**Duck Clicker:**

- Score saved per user in the database
- Only the initiating user can click
- Earn 2 dabloons every 5 clicks (4 with Double Points upgrade)
- Auto Clicker upgrade ticks every 60 seconds in the background — dabloons and quest progress accumulate even while you're not playing

**Tic Tac Toe:**

- Costs to play: `easy=2`, `medium=4`, `hard=8` dabloons
- Win rewards: `easy=4`, `medium=8`, `hard=16` dabloons
- Board updates live with button interactions
- Custom X/O symbols purchasable from the shop (⭐ and 💫)

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

### 📋 Daily Quests

A dynamic daily quest system that encourages interaction across the bot's features.
Quests refresh every day and scale with your level.

| **/**         | **what it does**                           |
| ------------- | ------------------------------------------ |
| **`/quests`** | View your current daily quests.            |
| **`/level`**  | View your level and needed XP to level up. |

**How it works:**

- Each day, a shared pool of quests is generated
- You unlock more quests as your level increases (up to 5)
- Progress is tracked automatically as you use the bot

**Quest types include:**

- Emoji usage — send a specific emoji multiple times
- Word usage — repeat a specific word in chat
- Tic Tac Toe — win games against the AI
- Duck Clicker — reach a click target based on your level (Auto Clicker counts toward this)

**Features:**

- Daily random target word and emoji
- Level-based scaling for difficulty and rewards
- Per-user progress tracking stored in the database
- Interactive claim buttons for completed quests
- Rewards include dabloons and XP

Quests are designed to be slightly chaotic, sometimes embarrassing, and always fun.

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

**Welcome message placeholders:** `{user}` — mentions the new member · `{server}` — inserts the server name

All moderation actions are automatically logged to the configured log channel.

---

### 💬 Message Events

| trigger                | what it does                                                                              |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Reply with **`4k`**    | Quote the replied message as an image. Also forwards to the configured 4k channel if set. |
| Reply with **`pin`**   | Pin the replied message.                                                                  |
| Reply with **`unpin`** | Unpin the replied message.                                                                |

> Amber must be a member of the server for these to work.

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

This checks for new commits, pulls them, updates dependencies if `requirements.txt` changed, and tells you to run `main.py`.

---

### Manual Setup

If you prefer to set things up yourself:

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
pip install torch transformers accelerate
```

1. Download the model:

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("Novodude/domesticated-LLM")
tokenizer = AutoTokenizer.from_pretrained("Novodude/domesticated-LLM")
model.save_pretrained("domesticated-LLM")
tokenizer.save_pretrained("domesticated-LLM")
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
- [x] Shop system with upgrades, food, accessories, colors
- [x] Pet system — cat companion powered by domesticated-LLM
- [x] LLM integration (domesticated-LLM — cat-speak fine-tune of SmolLM2-135M)
- [x] Auto setup script (amber.py) and updater (update.py)
- [x] Anime commands — waifu, husbando, neko, kitsune, quote
- [x] Shop upgrades fully implemented (Auto Clicker, Double Points, Custom X/O)
- [x] 4k channel forwarding
- [ ] Gambling system

---

## The Model — domesticated-LLM

The pet system uses **domesticated-LLM**, a fine-tuned version of `SmolLM2-135M-Instruct` trained on 20,000 synthetic cat-speak examples across 8 behavior styles (food, play, sleep, affection, grooming, alarm, boredom, comfort).

Given an instruction and a context (the owner's last message), it generates a response like a small chaotic cat would. The model lives locally at `./domesticated-LLM/` and is loaded lazily on first use.

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
- **ffmpeg** — required for audio processing in `/radio`
  > Download at [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

---

## License

MIT License — Copyright (c) 2025 Novodude and the AKO™ Team
