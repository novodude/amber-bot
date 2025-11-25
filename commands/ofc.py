import os
import random
import discord
from discord import app_commands
from pathlib import Path

# Path to the repo root
ROOT_DIR = Path(__file__).resolve().parent.parent
OFC_SFW = ROOT_DIR / "assets" / "ofc" / "sfw"
OFC_NSFW = ROOT_DIR / "assets" / "ofc" / "nsfw"

async def ofc_setup(bot):

    class OFCType(discord.Enum):
        SFW = "sfw"
        NSFW = "nsfw"

    @bot.tree.command(name="ofc", description="out of context image :3")
    @app_commands.describe(type="Choose whether the image is SFW or NSFW")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ofc(interaction: discord.Interaction, type: OFCType = OFCType.SFW):

        # check if NSFW is selected in a non-NSFW channel
        if type == OFCType.NSFW:
            if interaction.guild is not None:
                channel = interaction.channel
                if not isinstance(channel, discord.TextChannel) or not channel.is_nsfw():
                    return await interaction.response.send_message(
                        "NSFW images can only be requested in NSFW channels.",
                        ephemeral=True
                    )
        img_dir = OFC_SFW if type == OFCType.SFW else OFC_NSFW
        img = random.choice(os.listdir(img_dir))
        embed = discord.Embed(color=discord.Color.purple())
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="thanks to AMTA community <3")

        await interaction.response.send_message(
            file=discord.File(img_dir / img),
            embed=embed
        )
