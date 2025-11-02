# Amber the Discord Bot

---

## What is Amber?

---

Amber is a Discord bot with a growing set of fun and interactive features.  
The name comes from my pet duck, Amber.  
Right now, it includes the `/do`, `/ping`, and `/duck` commands, with more features added regularly.

---

## Commands

---

|**/**|**description**|**how I made it?**|
|---|---|---|
|**`/do`**|Lets users perform fun actions (like hug, slap, laugh, etc.) using random GIFs fetched from [nekos.best](https://nekos.best/). Each action has its own color, emoji, and description shown in an embed.|I made it by creating a dictionary of actions (with colors, emojis, and text), then used `aiohttp` to fetch GIFs asynchronously from the API. The command builds an embed with the right action info and sends it as a reply. It handles self, user, or no-user cases and includes error handling for failed requests.|
|**`/ping`**|Checks the bot's latency and responds with how fast it is (in milliseconds).|I used `bot.latency` to measure the delay between the bot and Discord's servers, multiplied by 1000 to get milliseconds. The command replies with a simple "Pong!" message showing the latency value.|
|**`/duck`**|Fetches a random duck GIF from [random-d.uk](https://random-d.uk/) and displays it in an embed.|I made it using `aiohttp` to asynchronously fetch a list of available duck GIFs from the Random Duck API (`https://random-d.uk/api/v2/list`). The command picks one at random and embeds it with the title "Random Duck!". If no list is available, it falls back to the `/random` endpoint. It supports use in servers, DMs, and private channels.|
|**`/rarch`**|Generates a unique, symmetrical inkblot image reminiscent of Rorschach tests.|I created this using PIL (Python Imaging Library) to generate random, symmetrical inkblot patterns. The command creates various shapes (ellipses, polygons, irregular blobs) on one half of the image, then mirrors it for symmetry. It adds random noise and splatters for texture, then sends the image as an embed asking "what do you see?", it's a suggestionfrom my best friend natalie hehe|
|**`/duck`**|Fetches a random duck GIF from [random-d.uk](https://random-d.uk/) and displays it in an embed.|I made it using `aiohttp` to asynchronously fetch a list of available duck GIFs from the Random Duck API (`https://random-d.uk/api/v2/list`). The command picks one at random and embeds it with the title “Random Duck!”. If no list is available, it falls back to the `/random` endpoint. It supports use in servers, DMs, and private channels.|

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

4. Create a `.env` file and add your Discord bot token:
```bash
echo "TOKEN=your_bot_token_here" > .env
```

5. Run the bot:
```bash
python main.py
```
    

---

## To-Do List

---

-  [x] Add `/duck` (Completed!)
-  [x] Add `/rarch` inkblot generator (Completed!)
- [ ] Add a simple game
- [ ] Add gambling (because why not)
- [ ] Train a simple LLM model and link it to the bot
- [ ] Add `/fact`, `/quote`, and `/8ball`
- [ ] Add a leveling system
    

---

## Dependencies

---

Required packages are listed in `requirement.txt`:

- **discord.py** (for Discord bot interaction)
- **python-dotenv** (for secure token loading)
- **aiohttp** (for asynchronous API requests, used internally by discord.py)
- **pillow** (PIL, for image generation in `/rarch` command)

Install dependencies with:
```bash
pip install -r requirement.txt
```

---

## Contributing

---

If you’d like to contribute:

1. Fork the repository.
    
2. Create a new branch for your feature or fix.
    
3. Submit a pull request with a clear explanation of what you changed.
    

Contributions are welcome — just remember to **keep proper credit** to _Novodude and the AKO™ Team_.

---

## License

---

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Novodude and the AKO™ Team

---
