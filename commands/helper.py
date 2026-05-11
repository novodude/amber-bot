import discord
from discord import app_commands, ui

# ─────────────────────────────────────────────
# Command data — update this when adding commands
# ─────────────────────────────────────────────

COMMANDS = {
    "🎭 Fun": [
        ("/do [action] [user]",        "Anime action GIF — hug, kiss, pat, kick, yeet, baka, peck and more"),
        ("/look [reaction]",           "Anime reaction GIF — blush, shrug, angry, happy and more"),
        ("/ofc [type]",     "Out-of-context image"),
        ("/8ball [question]",          "Ask the magic 8 ball"),
        ("/coinflip",                  "Flip a coin"),
        ("/no",                        "Get a random rejection reason"),
        ("/yes",                       "Get a random agreement reason"),
        ("/rate [user]",               "Get a detailed rating breakdown across 6 categories"),
        ("/mimic start [user]",        "Activate mimic mode for a user"),
        ("/mimic stop [user]",         "Stop mimic mode for a user"),
        ("/mimic list",                "List of users that Amber mimics"),
    ],
   "🌸 Anime": [
        ("/anime waifu",               "Get a random anime waifu image"),
        ("/anime husbando",            "Get a random anime husbando image"),
        ("/anime neko",                "Get a random anime neko image"),
        ("/anime kitsune",             "Get a random anime kitsune image"),
        ("/anime quote",               "Get a random anime quote"),
    ],
    "🦆 amber": [
        ("/quests", "View your daily quests and claim rewards"),
        ("/level",  "Check your current level and XP progress"),
    ],
    "🐾 Animals": [
        ("/animal duck",     "Get a random duck image 🦆"),
        ("/animal cat",      "Get a random cat gif + fact 🐱"),
        ("/animal dog",      "Get a random dog gif 🐶"),
        ("/animal fox",      "Get a random fox image 🦊"),
        ("/animal rotta",    "Get a random rat gif 🐀"),
        ("/animal bird",     "Random bird image + fact 🐦"),
        ("/animal panda",    "Random panda image + fact 🐼"),
        ("/animal redpanda", "Random red panda image + fact 🦊"),
        ("/animal koala",    "Random koala image + fact 🐨"),
        ("/animal kangaroo", "Random kangaroo image + fact 🦘"),
        ("/animal bunny",    "Get a random bunny image 🐰"),
    ],
    "💰 Economy": [
        ("/register",                    "Register in the system (50 starter dabloons)"),
        ("/profile",                     "View your profile — bio, balance, customization"),
        ("/setbio [bio]",                "Set your profile bio"),
        ("/money balance",               "Check your current dabloons balance"),
        ("/money daily",                 "Claim your daily dabloons (24h cooldown)"),
        ("/money give [user] [amount]",  "Send dabloons to another registered user"),
        ("/money beg"                 ,  "Beg users for dabloons"),
        ("/money rob [user]",            "Attempt to rob another user (risky!)"),
    ],
    "🛒 Shop": [
        ("/shop browse",         "Browse all shop categories"),
        ("/shop buy [item]",     "Purchase an item by name"),
        ("/shop inventory",      "View consumables and accessories you own"),
        ("/shop mypurchases",    "View your permanent unlocks"),
    ],
    "🐱 Pet": [
        ("/pet adopt [name]",          "Adopt your cat companion"),
        ("/pet status",                "Check your cat's hunger, happiness, and level"),
        ("/pet feed [item]",           "Feed your cat using food from your inventory"),
        ("/pet play",                  "Play with your cat (1h cooldown)"),
        ("/pet candy [item]",          "Use candy to give your pet a direct XP boost"),
        ("/pet equip [slot] [item]",   "Equip an accessory to your cat"),
        ("/pet unequip [slot]",        "Remove an item from a slot"),
        ("/pet rename [name]",         "Give your cat a new name"),
    ],
    "🖼️ Image": [
        ("/image wanted [user] [amount]",        "Create a wanted poster for a user"),
        ("/image misquote [user] [message]",     "Generate a fake quote image"),
        ("/image rarch",                         "Random Rorschach inkblot"),
        ("/image caption [caption] [image/url]", "Add a caption to an image"),
        ("/image meme [caption] [image/url]",    "Add a meme-style caption (top or bottom)"),
        ("/image grayscale [image/url]",         "Convert to grayscale"),
        ("/image blur [image/url]",              "Apply a blur effect"),
        ("/image rotate [angle] [image/url]",    "Rotate — 90°, 180°, or 360°"),
        ("/image flip [axis] [image/url]",       "Flip horizontally, vertically, or both"),
        ("/image invert [image/url]",            "Invert image colors"),
        ("/image pixelate [image/url]",          "Pixelate an image"),
        ("/image deepfry [image/url]",           "Deep fry an image"),
        ("/image edgedetect [image/url]",        "Apply edge detection filter"),
        ("/image rainbow [image/url]",           "Overlay a rainbow gradient"),
        ("/image sepia [image/url]",             "Apply sepia tone"),
        ("/image emboss [image/url]",            "Apply emboss effect"),
        ("/image solarize [image/url]",          "Apply solarize effect"),
        ("/image posterize [image/url]",         "Apply posterize effect"),
        ("/image glitch [image/url]",            "Apply glitch effect"),
        ("/image swirl [image/url]",             "Apply swirl/warp effect"),
    ],
    "⚙️ Utils": [
        ("/say embed [message]",          "Make Amber say your message in embed"),
        ("/say text [message]",           "Make Amber say your message in text"),
        ("/download [url]",               "Download audio from YouTube"),
        ("/melody",                       "Generate a short WAV melody"),
        ("/user info [user]",             "Get information about a user"),
        ("/user avatar [user]",           "Get a user's avatar"),
        ("/user banner [user]",           "Get a user's banner"),
        ("/my stats [type]",              "View your action stats — given or received"),
    ],
    "🎮 Games": [
        ("/games duck_clicker",              "Click ducks to earn dabloons — 2 per 5 clicks (4 with Double Points). Auto Clicker ticks every 60s in the background."),
        ("/games tic_tac_toe [difficulty]",  "Play Tic Tac Toe vs AI — easy / medium / hard. Custom symbols available from the shop."),
        ("/games trivia",                    "Answer a trivia question"),
    ],
    "📻 Radio": [
        ("/radio play [playlist_id] [source_url] [mix_mode]", "Play a saved playlist, stream a direct YouTube URL, or shuffle everything with mix mode"),
        ("/radio queue [source_url]",                         "Add a YouTube URL to the current queue without interrupting playback"),
        ("/radio add [name] [url] [public]",                  "Create a playlist from a YouTube or Spotify URL — syncs in the background with a live progress bar"),
        ("/radio sync [playlist_id]",                         "Re-sync a playlist from its source URL — runs in the background"),
        ("/radio libraries [public]",                         "Browse your playlists or public ones"),
        ("/radio remove [playlist_id]",                       "Delete a playlist and all its songs (owner only)"),
        ("/radio songs [playlist_id]",                        "View all songs in a playlist (paginated)"),
        ("/radio stop",                                       "Stop playback and disconnect from voice"),
    ],
    "🛡️ Admin": [
        ("/admin kick [member]",            "Kick a member  ·  requires Kick Members"),
        ("/admin ban [member]",             "Ban a member  ·  requires Ban Members"),
        ("/admin unban [user_id]",          "Unban a user by ID  ·  requires Ban Members"),
        ("/admin timeout [member] [dur]",   "Timeout a member (10m / 2h / 1d)  ·  requires Moderate Members"),
        ("/admin warn [member]",            "Warn a member and log it  ·  requires Kick Members"),
        ("/admin warnings [member]",        "View a member's warnings  ·  requires Kick Members"),
        ("/admin clear_warnings [member]",  "Clear all warnings for a member  ·  requires Kick Members"),
        ("/admin purge [n]",                "Bulk delete up to 100 messages  ·  requires Manage Messages"),
        ("/admin slowmode [seconds]",       "Set channel slowmode (0 to disable)  ·  requires Manage Channels"),
        ("/admin lockdown",                 "Toggle channel lockdown  ·  requires Manage Channels"),
        ("/admin unlockdown",               "Lift channel lockdown  ·  requires Manage Channels"),
    ],
    "⚙️ Server": [
        ("/server info",                      "Show server info — owner, members, channels, roles"),
        ("/server invite",                    "Generate a single-use 1-hour invite link"),
        ("/server icon",                      "Show the server icon"),
        ("/server banner",                    "Show the server banner"),
        ("/server set_prefix [prefix]",       "Set a custom command prefix (1–5 chars)  ·  Admin"),
        ("/server set_welcome [channel]",     "Set welcome channel + message via modal  ·  Admin"),
        ("/server set_welcome_off",           "Disable welcome messages  ·  Admin"),
        ("/server set_autorole [role]",       "Auto-assign a role to every new member  ·  Admin"),
        ("/server set_autorole_off",          "Disable autorole  ·  Admin"),
        ("/server set_log [channel]",         "Set the moderation log channel  ·  Admin"),
        ("/server set_4k_channel [channel]",  "Set a channel for 4k image results to be forwarded to  ·  Manage Channels"),
        ("/server set_4k_channel_off",        "Disable 4k channel forwarding  ·  Manage Channels"),
    ],
    "💬 Events": [
    ("Reply with `4k`",    "Quote the replied message as an image — also forwards to the 4k channel if configured"),
    ("Reply with `pin`",   "Pin the replied message"),
    ("Reply with `unpin`", "Unpin the replied message"),
    ],
    "🎲 Gamble": [
        ("/gamble coinflip [bet] [choice]", "Double your dabloons on a 50/50 flip"),
        ("/gamble roll [bet] [choice]",     "Bet on a dice roll for a 5x payout"),
        ("/gamble slots [bet]",             "Spin the slots for a chance at a 10x Jackpot"),
    ]
}
 
CATEGORY_COLORS = {
    "🎭 Fun":      discord.Color.from_rgb(255, 100, 130),
    "🌸 Anime":    discord.Color.from_rgb(255, 150, 200),
    "🦆 amber":    discord.Color.from_rgb(255, 170, 0),
    "🐾 Animals":  discord.Color.from_rgb(80, 200, 120),
    "💰 Economy":  discord.Color.from_rgb(255, 195, 40),
    "🛒 Shop":     discord.Color.from_rgb(255, 165, 0),
    "🐱 Pet":      discord.Color.from_rgb(255, 140, 50),
    "🎲 Gamble":   discord.Color.from_rgb(200, 0, 0),
    "🖼️ Image":    discord.Color.from_rgb(120, 170, 255),
    "⚙️ Utils":    discord.Color.from_rgb(160, 160, 160),
    "🎮 Games":    discord.Color.from_rgb(130, 100, 255),
    "📻 Radio":    discord.Color.from_rgb(40, 175, 255),
    "🛡️ Admin":    discord.Color.from_rgb(255, 100, 50),
    "⚙️ Server":   discord.Color.from_rgb(140, 140, 255),
    "💬 Events":   discord.Color.from_rgb(180, 180, 180),
}


def build_overview_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🦆 Amber — Help",
        description=(
            "Pick a category from the dropdown to browse commands.\n"
            "Use the **🔍 Search** button to find a specific command.\n\n"
            + "\n".join(
                f"{cat} — **{len(cmds)}** command{'s' if len(cmds) != 1 else ''}"
                for cat, cmds in COMMANDS.items()
            )
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="quacking good!")
    return embed


def build_category_embed(category: str) -> discord.Embed:
    color = CATEGORY_COLORS.get(category, discord.Color.blurple())
    embed = discord.Embed(title=f"{category} Commands", color=color)
    for cmd, desc in COMMANDS[category]:
        embed.add_field(name=cmd, value=desc, inline=False)
    embed.set_footer(text="Use the dropdown to browse categories • 🔍 Search for a specific command")
    return embed


def search_commands(query: str) -> list[tuple[str, str, str]]:
    query = query.lower()
    results = []
    for category, commands in COMMANDS.items():
        for cmd, desc in commands:
            if query in cmd.lower() or query in desc.lower():
                results.append((category, cmd, desc))
    return results


# ─────────────────────────────────────────────
# Search Modal
# ─────────────────────────────────────────────
class SearchModal(ui.Modal, title="🔍 Search Commands"):
    query = ui.TextInput(
        label="What are you looking for?",
        placeholder="e.g. ban, dabloons, radio, welcome...",
        min_length=1,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        results = search_commands(str(self.query))

        if not results:
            embed = discord.Embed(
                title=f'🔍 No results for "{self.query}"',
                description="Try a different keyword.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title=f'🔍 Results for "{self.query}"',
                description=f"Found **{len(results)}** command{'s' if len(results) != 1 else ''}",
                color=discord.Color.blurple()
            )
            for category, cmd, desc in results[:15]:
                embed.add_field(
                    name=cmd,
                    value=f"{desc}\n*— {category}*",
                    inline=False
                )
            if len(results) > 15:
                embed.set_footer(text=f"Showing first 15 of {len(results)} — try a more specific search")
            else:
                embed.set_footer(text="Use the dropdown below to browse by category")

        await interaction.response.edit_message(embed=embed)


# ─────────────────────────────────────────────
# Category Select
# ─────────────────────────────────────────────
class CategorySelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Overview",
                value="overview",
                emoji="🏠",
                description="Show all categories"
            )
        ] + [
            discord.SelectOption(
                label=cat.split(" ", 1)[1],   # label without the leading emoji
                value=cat,
                emoji=cat.split(" ")[0],
                description=f"{len(cmds)} command{'s' if len(cmds) != 1 else ''}"
            )
            for cat, cmds in COMMANDS.items()
        ]
        super().__init__(
            placeholder="📂  Browse a category...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        embed = build_overview_embed() if choice == "overview" else build_category_embed(choice)
        await interaction.response.edit_message(embed=embed)


# ─────────────────────────────────────────────
# Help View
# ─────────────────────────────────────────────
class HelpView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CategorySelect())

    @ui.button(label="🔍 Search", style=discord.ButtonStyle.secondary, row=1)
    async def search_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SearchModal())

    @ui.button(label="🏠 Overview", style=discord.ButtonStyle.primary, row=1)
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(embed=build_overview_embed())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ─────────────────────────────────────────────
# Register the command
# ─────────────────────────────────────────────
async def help_setup(bot):
    @bot.tree.command(name="help", description="Browse all of Amber's commands")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def help_command(interaction: discord.Interaction):
        view = HelpView()
        await interaction.response.send_message(
            embed=build_overview_embed(),
            view=view,
            ephemeral=True
        )
