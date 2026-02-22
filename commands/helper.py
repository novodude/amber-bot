import discord
from discord import app_commands, ui

# ─────────────────────────────────────────────
# Command data — update this when adding commands
# ─────────────────────────────────────────────
COMMANDS = {
    "🎭 Fun": [
        ("/do [action] [user]",        "Anime action GIF — hug, kiss, pat, kick, yeet, baka and more"),
        ("/look [reaction]",           "Anime reaction GIF — blush, shrug, angry, happy and more"),
        ("/rarch",                     "Generate a random Rorschach inkblot image"),
        ("/ofc [type]",                "Random out-of-context image (SFW or NSFW channels only)"),
        ("/wanted [user] [amount]",    "Create a wanted poster for someone"),
        ("/misquote [user] [message]", "Put words in someone's mouth"),
        ("/melody",                    "Generate a short WAV melody — notes or beats mode"),
        ("/8ball [question]",          "Ask the magic 8 ball"),
        ("/coinflip",                  "Flip a coin"),
        ("/no",                        "Get a random rejection reason"),
        ("/yes",                       "Get a random agreement reason"),
        ("/rate [user]",               "Get a detailed rating breakdown across 6 categories"),
        ("/download [url]",            "Download audio from a YouTube URL and upload to Catbox"),
    ],
    "🐾 Animals": [
        ("/duck",   "Random duck GIF 🦆"),
        ("/cat",    "Random cat GIF 🐱"),
        ("/rotta",  "Random rat GIF 🐀"),
    ],
    "💰 Economy": [
        ("/register",                    "Register in the system (50 starter dabloons)"),
        ("/profile",                     "View your profile — bio, balance, customization"),
        ("/setbio [bio]",                "Set your profile bio"),
        ("/money balance",               "Check your current dabloons balance"),
        ("/money daily",                 "Claim your daily dabloons (24h cooldown)"),
        ("/money give [user] [amount]",  "Send dabloons to another registered user"),
    ],
    "🎮 Games": [
        ("/games duck_clicker",              "Click ducks to earn dabloons — 2 per 5 clicks"),
        ("/games tic_tac_toe [difficulty]",  "Play Tic Tac Toe vs AI — easy / medium / hard"),
    ],
    "📻 Radio": [
        ("/radio [playlist_id]",    "Play a saved playlist (or enable mix mode for all playlists)"),
        ("/radio_add [name] [url]", "Create a new playlist from a YouTube or Spotify URL"),
        ("/radio_libraries",        "Browse your playlists or public ones"),
        ("/radio_remove [id]",      "Delete a playlist and its songs (owner only)"),
        ("/radio_sync [id]",        "Re-download songs from the playlist source URL"),
        ("/radio_songs [id]",       "View all songs in a playlist (paginated)"),
        ("/radio_stop",             "Stop playback and disconnect from voice"),
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
        ("/server info",                    "Show server info — owner, members, channels, roles"),
        ("/server invite",                  "Generate a single-use 1-hour invite link"),
        ("/server icon",                    "Show the server icon"),
        ("/server banner",                  "Show the server banner"),
        ("/server set_prefix [prefix]",     "Set a custom command prefix (1–5 chars)  ·  Admin"),
        ("/server set_welcome [channel]",   "Set welcome channel + message via modal  ·  Admin"),
        ("/server set_welcome_off",         "Disable welcome messages  ·  Admin"),
        ("/server set_autorole [role]",     "Auto-assign a role to every new member  ·  Admin"),
        ("/server set_autorole_off",        "Disable autorole  ·  Admin"),
        ("/server set_log [channel]",       "Set the moderation log channel  ·  Admin"),
    ],
    "💬 Events": [
        ("Reply with `4k`",    "Quote the replied message as an image"),
        ("Reply with `pin`",   "Pin the replied message"),
        ("Reply with `unpin`", "Unpin the replied message"),
    ],
}

CATEGORY_COLORS = {
    "🎭 Fun":     discord.Color.from_rgb(255, 100, 130),
    "🐾 Animals": discord.Color.from_rgb(80, 200, 120),
    "💰 Economy": discord.Color.from_rgb(255, 195, 40),
    "🎮 Games":   discord.Color.from_rgb(130, 100, 255),
    "📻 Radio":   discord.Color.from_rgb(40, 175, 255),
    "🛡️ Admin":   discord.Color.from_rgb(255, 100, 50),
    "⚙️ Server":  discord.Color.from_rgb(140, 140, 255),
    "💬 Events":  discord.Color.from_rgb(180, 180, 180),
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
