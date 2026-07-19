from discord import app_commands
from discord import app_commands
from utils.text import uwuify, text_count, text_find, text_replace
import aiohttp
import aiohttp
import discord
import re
import urllib.parse


@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class TextCommands(app_commands.Group):
    """Group of text manipulation commands."""

    def __init__(self):
        super().__init__(
            name="text",
            description="Commands for manipulating and analyzing text."
        )

    @app_commands.command(name="uwu", description="Convert text into uwu-speak")
    @app_commands.describe(
        text="The text to uwu-ify.",
        stutter="Chance (0-100%) of stuttering words, e.g. 'p-pinky'. Default 10%.",
        faces="Chance (0-100%) of adding a kaomoji face at the end. Default 30%.",
        word_swaps="Swap common words like 'you' -> 'uwu', 'love' -> 'wuv'. Default off."
    )
    async def uwu(
        self, interaction: discord.Interaction, text: str,
        stutter: app_commands.Range[int, 0, 100] = 10,
        faces: app_commands.Range[int, 0, 100] = 30,
        word_swaps: bool = False
    ):
        result = uwuify(text, stutter_chance=stutter / 100, face_chance=faces / 100, word_swaps=word_swaps)
        await interaction.response.send_message(result)

    @app_commands.command(name="count", description="Get stats about a piece of text")
    @app_commands.describe(
        text="The text to analyze.",
        target="Optional: count occurrences of this word/substring too."
    )
    async def count(self, interaction: discord.Interaction, text: str, target: str = None):
        stats = text_count(text, target)

        embed = discord.Embed(title="Text Stats", color=discord.Color.blurple())
        embed.add_field(name="Characters", value=stats["characters"])
        embed.add_field(name="Characters (no spaces)", value=stats["characters_no_spaces"])
        embed.add_field(name="Words", value=stats["words"])
        embed.add_field(name="Lines", value=stats["lines"])

        if target:
            embed.add_field(
                name=f'Occurrences of "{target}"',
                value=stats["target_occurrences"],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="find", description="Find all positions of a word/substring in text")
    @app_commands.describe(
        text="The text to search in.",
        target="The word or substring to find.",
        case_sensitive="Whether the search should be case-sensitive. Default off."
    )
    async def find(
        self, interaction: discord.Interaction, text: str, target: str,
        case_sensitive: bool = False
    ):
        positions = text_find(text, target, case_sensitive)

        if not positions:
            await interaction.response.send_message(f'"{target}" was not found in the text.')
            return

        await interaction.response.send_message(
            f'Found "{target}" at {len(positions)} position(s): {positions}'
        )

    @app_commands.command(name="replace", description="Replace occurrences of a word/substring in text")
    @app_commands.describe(
        text="The text to modify.",
        target="The word or substring to replace.",
        replacement="What to replace it with.",
        case_sensitive="Whether the match should be case-sensitive. Default off.",
        limit="Max number of replacements to make. Default -1 (replace all)."
    )
    async def replace(
        self, interaction: discord.Interaction, text: str, target: str, replacement: str,
        case_sensitive: bool = False, limit: int = -1
    ):
        result = text_replace(text, target, replacement, case_sensitive, limit)
        await interaction.response.send_message(result)


UD_API_URL = "https://api.urbandictionary.com/v0/define"
UD_DEFINE_URL = "https://www.urbandictionary.com/define.php"


def _linkify_ud_brackets(text: str | None) -> str:
    """Urban Dictionary wraps linked terms in [brackets] — turn each into
    a markdown link to that term's own UD page, e.g. [fuck](https://...)."""
    if not text:
        return ""

    def replace(match):
        term = match.group(1)
        url = f"{UD_DEFINE_URL}?{urllib.parse.urlencode({'term': term})}"
        return f"[{term}]({url})"

    return re.sub(r"\[(.+?)\]", replace, text)


async def fetch_urban_definitions(term: str, limit: int = 10) -> list[dict]:
    """Fetch up to `limit` definitions for `term` from Urban Dictionary."""
    async with aiohttp.ClientSession() as session:
        async with session.get(UD_API_URL, params={"term": term}) as resp:
            data = await resp.json()
            return data.get("list", [])[:limit]


class UrbanPaginator(discord.ui.View):
    """Previous/Next button pager for a list of Urban Dictionary definitions."""

    def __init__(self, term: str, definitions: list[dict], author_id: int):
        super().__init__(timeout=120)
        self.term = term
        self.definitions = definitions
        self.author_id = author_id
        self.index = 0
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.index == 0
        self.next_button.disabled = self.index >= len(self.definitions) - 1

    def make_embed(self) -> discord.Embed:
        entry = self.definitions[self.index]

        embed = discord.Embed(
            title=entry.get("word", self.term),
            description=_linkify_ud_brackets(entry.get("definition", "")[:3500]),
            color=discord.Color.blue(),
            url=entry.get("permalink")
        )

        example = _linkify_ud_brackets(entry.get("example", "")[:900])
        if example:
            embed.add_field(name="Example", value=example[:1024], inline=False)

        likes = entry.get("thumbs_up", 0)
        dislikes = entry.get("thumbs_down", 0)
        
        embed.set_footer(
            text=f"Definition {self.index + 1}/{len(self.definitions)} • by {entry.get('author', 'unknown')} • 👍 {likes} | 👎 {dislikes}"
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can flip through definitions.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        # Note: editing after timeout needs the original message reference,
        # which this view doesn't hold — see note below the code block.



async def text_setup(bot):
    bot.tree.add_command(TextCommands())

    @bot.tree.command(name="urban", description="Look up a phrase on Urban Dictionary")
    @app_commands.describe(
        term="The word or phrase to look up.",
        private="Results only show to you?"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def urban(interaction: discord.Interaction, term: str, private: bool = False):
        await interaction.response.defer(ephemeral=private)

        definitions = await fetch_urban_definitions(term, limit=10)

        if not definitions:
            await interaction.followup.send(f'No definitions found for "{term}".', ephemeral=private)
            return

        view = UrbanPaginator(term, definitions, author_id=interaction.user.id)
        await interaction.followup.send(embed=view.make_embed(), view=view, ephemeral=private)
