# Amber the Discord Bot

---

## What is Amber?

---

Amber is a Discord bot with a growing set of fun and interactive features.  
The name comes from my pet duck, Amber.  
Right now, it includes the `/do`, `/rarch`, `/ofc`, commands, with more features added regularly.

---

## Commands

---

| **/**           | **description**                                                                                             | **how I made it?**                                                                                                                                                                       |
| --------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`/do`**       | Anime action images (hug, slap, laugh, etc.) using random GIFs from [nekos.best](https://nekos.best/).      | Built from a dictionary of actions (colors, emojis, text) and `aiohttp` to fetch GIFs asynchronously; embeds are built per-action and the command handles self/no-user cases and errors. |
| **`/ping`**     | Checks the bot's latency.                                                                                   | Uses `bot.latency` multiplied by 1000 to report milliseconds.                                                                                                                            |
| **`/duck`**     | Fetches a random duck GIF from [random-d.uk](https://random-d.uk/) and displays it in an embed.             | Uses `aiohttp` to fetch the duck list from `https://random-d.uk/api/v2/list`, picks one at random, and falls back to `/random` if needed.                                                |
| **`/cat`**      | Fetches a random cat image.                                                                                 | fetches a cat image from TheCatAPI and embeds it (see commands/animals.py).                                                                                                              |
| **`/rat`**      | Fetches a random rat GIF.                                                                                   | Uses Giphy's random endpoint with the project's `GIPHY_API` environment variable to fetch rat GIFs and embeds them (see commands/animals.py).                                            |
| **`/rarch`**    | Generates artistic, symmetrical inkblot images with dynamic color schemes reminiscent of Rorschach tests.   | Uses Pillow to create symmetrical patterns with layered shapes, noise, and Gaussian blur for more natural inkblots.                                                                      |
| **`/ofc`**      | Displays "out of context" images from local assets.                                                         | Serves images from assets/ofc (SFW/NSFW) and enforces NSFW channel checks when requested (see commands/ofc.py).                                                                          |
| **`/wanted`**   | Creates a "Wanted" poster for a user with their avatar and a bounty amount.                                 | Uses Pillow to composite the user's avatar onto a poster template, fits text with a TTF font, and returns a PNG (see commands/fun.py).                                                   |
| **`/melody`**   | Interactive melody generator that creates short WAV files from notes or beat patterns.                      | Provides a modal to enter notes or beats, generates audio with wavesynth, and returns a WAV attachment (see commands/melody.py).                                                         |
| **`/misquote`** | create a misquoted image of someone                                                                         | Uses Pillow to composite the user's avatar onto a canvas, fits text with a TTF font, and returns a PNG (see commands/fun.py).                                                            |
| **`/look`**     | Anime reaction images (happy, blush, angry, etc.) using random GIFs from [nekos.best](https://nekos.best/). | Built from a dictionary of actions (colors, emojis, text) and `aiohttp` to fetch GIFs asynchronously; embeds are built per-action and the command handles self/no-user cases and errors. |
| `/no`           | give ranodom rejection reasons                                                                              | -                                                                                                                                                                                        |

## **Radio system**

a local audio player that pull your YouTube and Spotify\* playlists
and sync it locally to play it later, it uses the `yt_dlp` to download the media from YouTube and convert it to `OPUS` format for more compatibility with discord, using `spotipy` to get the meta data of your Spotify playlists to allow `yt_dlp` to download it from youtube.

then the data get stored in a database managed using `aiosqlite` for more control.

| **/**              | **what it does?**                                                         |
| :----------------- | :------------------------------------------------------------------------ |
| `/radio`           | play your saved playlists using their id e.g `1` for your first playlist. |
| `/radio_libraries` | check your saved playlist.                                                |
| `/radio_add`       | add a new playlist.                                                       |
| `/radio_remove`    | remove playlist by id.                                                    |
| `/radio_stop`      | stop the radio and disconnect the bot                                     |
| `/radio_sync`      | sync the playlists using the link                                         |
| `/radio_songs`     | show you the songs of a playlist                                          |

# events

| what is it? |                                                                            what it does?                                                                            |
| :---------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|  **`4k`**   | event that act when replying to some one.<br>when you reply with `4k` to a message(while amber is a bot in the server) amber will quote the message you replied to. |
|    `pin`    |                                                               reply to a message with `pin` to pin it                                                               |
|   `unpin`   |                                                              reply to a message with `upin` to upin it                                                              |

---

## Setup

---

1. Clone the repository:

```bash
git clone https://github.com/novodude/amber-bot.git
cd amber-bot
```

2. Create a virtual environment and activate it:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirement.txt
```

4. get the required API keys:

- spotify api key: [spotify develober dashboard](https://developer.spotify.com/dashboard/applications)
- giphy api key: [the giphy docs](https://developers.giphy.com/docs/api#quick-start-guide)

5. Create a `.env` file and add your Discord bot token and other API key:

```bash
echo "TOKEN=your_bot_token_here" > .env
echo "GIPHY_API=your_giphy_api_key_here" >> .env
echo "SPOTIFY_CLIENT_ID=your_spotify_client_id_here" >> .env
echo "SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here" >> .env
```

5. Run the bot:

```bash
python main.py
```

---

## To-Do List

---

- [x] Add `/duck`
- [x] Add `/rarch` inkblot generator
- [x] Add `/cat` and `/rat` commands
- [x] Improve `/do` command with more actions and grammar and better error handling
- [x] Add `/ofc` command for out-of-context images
- [x] add `/melody` command to generate simple melodies
- [x] add `4k` to quote someone's message
- [ ] Add `/toe` command for tic-tac-toe games
- [ ] Add gambling (because why not)
- [ ] Train a simple LLM model and link it to the bot(40% done)

---

## Dependencies

---

- **ffmpeg**:
  required for audio processing in some commands (like `/radio`).
  > for installation instructions, visit the [FFmpeg download page](https://ffmpeg.org/download.html)
  > and follow the instructions for your operating system.

Required packages are listed in `requirement.txt`:

- **discord.py** (for Discord bot interaction)
- **python-dotenv** (for secure token loading)
- **aiohttp** (for asynchronous API requests, used internally by discord.py)
- **pillow** (PIL, for image generation in `/rarch` command)
- **wavesynth** (for creating the melodies in `/melody` command)
- **yt-dlp** (used in downloading audio for `/radio` command)
- **aiosqlite** (for controlling the database, used in `/radio` command)
- **spotipy** (to make Spotify based playlists in `/radio` command)

Install dependencies with:

```bash
pip install -r requirement.txt
```

## License

---

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Novodude

---
