from discord import app_commands
from typing import Literal
import discord

from utils.cypher import encode_text, decode_text, auto_decode

CypherFormat = Literal[
    "binary", "hex", "base64", "base32", "morse", "nato", "rot13", "url", "reverse"
]


@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class CypherCommands(app_commands.Group):
    """Group of text encoding/decoding (cypher) commands."""

    def __init__(self):
        super().__init__(
            name="cypher",
            description="Encode or decode text into various cypher formats."
        )

    @app_commands.command(name="encode", description="Encode text into a cypher format")
    @app_commands.describe(
        text="The text to encode.",
        format="Which format to encode into."
    )
    async def encode(self, interaction: discord.Interaction, text: str, format: CypherFormat):
        await interaction.response.defer()
        try:
            result = await encode_text(text, format)
            await interaction.followup.send(f"**{format}:**\n```\n{result}\n```")
        except Exception as e:
            await interaction.followup.send(f"An error occurred:\n```\n{e}\n```")

    @app_commands.command(name="decode", description="Decode cyphered text (auto-detects format if not given)")
    @app_commands.describe(
        text="The encoded text to decode.",
        format="The format it's encoded in — leave blank to auto-detect."
    )
    async def decode(
        self,
        interaction: discord.Interaction,
        text: str,
        format: CypherFormat | None = None
    ):
        await interaction.response.defer()
        try:
            if format is None:
                detected_format, result = await auto_decode(text)
                await interaction.followup.send(
                    f"**detected: {detected_format}**\n```\n{result}\n```"
                )
            else:
                result = await decode_text(text, format)
                await interaction.followup.send(f"**{format}:**\n```\n{result}\n```")
        except Exception as e:
            await interaction.followup.send(f"An error occurred:\n```\n{e}\n```")


async def cypher_setup(bot):
    bot.tree.add_command(CypherCommands())
