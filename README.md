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
|**`/ping`**|Checks the bot’s latency and responds with how fast it is (in milliseconds).|I used `bot.latency` to measure the delay between the bot and Discord’s servers, multiplied by 1000 to get milliseconds. The command replies with a simple “Pong!” message showing the latency value. It’s registered as a global slash command using `@bot.tree.command` and supports guilds, DMs, and private channels.|
|**`/duck`**|Fetches a random duck GIF from [random-d.uk](https://random-d.uk/) and displays it in an embed.|I made it using `aiohttp` to asynchronously fetch a list of available duck GIFs from the Random Duck API (`https://random-d.uk/api/v2/list`). The command picks one at random and embeds it with the title “Random Duck!”. If no list is available, it falls back to the `/random` endpoint. It supports use in servers, DMs, and private channels.|

---

## Setup

---

1. Clone the repository:
    
    `git clone https://github.com/yourusername/amber-bot.git cd amber-bot`
    
2. Install the required dependencies.
    
3. Create a `.env` file and add your bot token:
    
    `TOKEN=your_bot_token_here`
    
4. Run the bot:
    
    `python main.py`
    

---

## To-Do List

---

-  Add `/duck`
    
-  Add a simple game
    
-  Add gambling (because why not)
    
-  Train a simple LLM model and link it to the bot
    
-  Add `/fact`, `/quote`, and `/8ball`
    
-  Add a leveling system
    

---

## Dependencies

---

- **discord.py** (for Discord bot interaction)
    
- **aiohttp** (for asynchronous API requests)
    
- **python-dotenv** (for secure token loading)
    

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

`Amber Discord Bot   Copyright (c) 2025 Novodude and the AKO™ Team    You are free to use, modify, and share this code for personal or educational purposes.   However, you must give clear credit to the original creators: Novodude and the AKO™ Team.   You may not claim the project, its name, or its code as your own.    Commercial use is not permitted without explicit permission.`

---