from commands.image import ImageGenerator
from utils.economy import get_4k_channel_id
from discord import app_commands
from discord.ext import commands
from typing import Optional
from pathlib import Path
import statistics
import discord
import aiohttp
import random
import json
import os

class OFCType(discord.Enum):
    SFW = "sfw"
    NSFW = "nsfw"

async def fun_setup(bot: commands.Bot):
    """Set up fun commands for the bot."""
    ROOT_DIR = Path(__file__).resolve().parent.parent
    OFC_SFW = ROOT_DIR / "assets" / "ofc" / "sfw"
    OFC_NSFW = ROOT_DIR / "assets" / "ofc" / "nsfw"
    
    
    # ==================== Out of Context ====================
    @bot.tree.command(name="ofc", description="Get a random out of context image")
    @app_commands.describe(type="Choose whether the image is SFW or NSFW")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ofc(interaction: discord.Interaction, type: OFCType = OFCType.SFW):
        # Check NSFW restrictions
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
        embed.set_footer(text="Thanks to AMTA community <3")
        
        await interaction.response.send_message(
            file=discord.File(img_dir / img),
            embed=embed
        )

    # ==================== Games ====================
    @bot.tree.command(name="8ball", description="Ask the magic 8 ball a question")
    @app_commands.describe(question="Your question for the magic 8 ball")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def eight_ball(interaction: discord.Interaction, question: str):
        answers = [
            # ── Original 20 ──────────────────────────────────────────
            "It is certain", "It is decidedly so", "Without a doubt",
            "Yes, definitely", "You may rely on it", "As I see it, yes",
            "Most likely", "Outlook good", "Yes", "Signs point to yes",
            "Reply hazy, try again", "Ask again later", "Better not tell you now",
            "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful",

            # ── Positive / yes ───────────────────────────────────────
            "Bestie yes", "Slay, go for it", "No cap, absolutely",
            "It's giving yes", "The universe said yes bestie",
            "Real and true", "Bet", "Understood, yes",
            "We are so back", "This is your sign fr",
            "Main character behavior, do it", "Rent free in the yes zone",
            "Periodt", "Ate and left no crumbs, yes",

            # ── Negative / no ────────────────────────────────────────
            "Nope, not today", "That's a hard no from me",
            "Ick. No.", "We are so not doing this",
            "No and I said what I said", "The audacity... no",
            "It's giving no", "Understood, no, goodbye",
            "Delulu behavior, stop", "Touch grass first then ask again",
            "This is not it chief", "Sending no thoughts your way",

            # ── Vague / try again ────────────────────────────────────
            "Idk bestie idk", "That's so real but also unclear",
            "The vibes are mixed", "Say less... actually say more",
            "Big maybe energy", "My roman empire is uncertainty",
            "Not giving you an answer rn", "Living rent free in the maybe zone",
            "Manifestation pending", "The lore is still unfolding",
            "Ask again after you eat something", "I'm in my flop era, try later",
            "This is so real but also who knows", "Understood the assignment, unclear on the answer",
        ]
        
        embed = discord.Embed(title="🎱 The Magic 8 Ball 🎱", color=discord.Color.blurple())
        embed.add_field(name="Question:", value=question, inline=False)
        embed.add_field(name="Answer:", value=random.choice(answers), inline=False)
        embed.set_footer(text="Amber is not responsible for any decisions based on this answer.")
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="coinflip", description="Flip a coin")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def coinflip(interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(title="Coin Flip!", color=discord.Color.gold())
        embed.description = f"The coin landed on **{result}**!"
        
        await interaction.response.send_message(embed=embed)
    @bot.tree.command(name="no", description="say no!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def no(interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://naas.isalman.dev/no") as resp:
                data= await resp.json()
    

        embed = discord.Embed(
            color=discord.Color.red(),
            title="no!",
            description=f"{data.get('reason', 'no response')}"
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="yes", description="agreement reason")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def yes(interaction: discord.Interaction):
        with open("assets/fun/yes.json") as yes:
            reasons = json.load(yes)
        response = random.choice(reasons)
        embed = discord.Embed(
            color=discord.Color.brand_green(),
            title="yes!",
            description=response
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="rate", description="give you detailed rating")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rate(interaction: discord.Interaction, user: Optional[discord.User] = None):
        try:
            await interaction.response.defer()
            user = user or interaction.user
            
            ratings = {
                "Smort": random.randint(0, 100),
                "Funny": random.randint(0, 100),
                "Rizz": random.randint(0, 100),
                "Hot": random.randint(0, 100),
                "cute": random.randint(0, 100),
                "gay": random.randint(0, 100)
            }

            mean_rating = statistics.mean(ratings.values())

            with open("assets/fun/rating.json", "r") as f:
                data = json.load(f)

            if mean_rating >= 75:
                description = data.get("high", [])
            elif mean_rating >= 40:
                description = data.get("medium", [])
            else:
                description = data.get("low", [])

            embed = discord.Embed(
                title=f"Rating for {user.display_name}",
                color=discord.Color.pink(),
                description=random.choice(description).format(**ratings)
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Smort", value=f"**{ratings['Smort']}%** 🤓", inline=True)
            embed.add_field(name="Funny", value=f"**{ratings['Funny']}%** 😜", inline=True)
            embed.add_field(name="Rizz", value=f"**{ratings['Rizz']}%** 😗", inline=True)
            embed.add_field(name="Hot", value=f"**{ratings['Hot']}%** 🔥", inline=True)
            embed.add_field(name="Cute", value=f"**{ratings['cute']}%** 🫶", inline=True)
            embed.add_field(name="Gay", value=f"**{ratings['gay']}%** 🏳️‍🌈", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Error",
                        description=f"```log\nError:\n{str(e)}\n```",
                        color=discord.Color.red()
                    )
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Error",
                        description=f"```log\nError:\n{str(e)}\n```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

async def handle_4k(bot: commands.Bot, message: discord.Message):
    if message.author.bot or message.content.lower().strip() != "4k":
        return

    if not message.guild:
        return

    if not message.reference or not getattr(message.reference, "message_id", None):
        await message.reply("Reply to a message to use `4k`.", delete_after=2)
        return

    # Try cache first, fallback to fetch
    replied = message.reference.resolved
    if not isinstance(replied, discord.Message):
        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
        except Exception:
            await message.reply("Can't read the replied message.", delete_after=2)
            return

    ROOT_DIR = Path(__file__).resolve().parent.parent
    img_gen = ImageGenerator(ROOT_DIR)

    try:
        output_bytes = await img_gen.create_quote_image(
            replied.author,
            replied.content or ""
        )
    except Exception as e:
        await message.reply(f"Error: {e}", delete_after=5)
        return

    filename = f"quote_{replied.author.id}.png"

    # ── Send image in current channel ─────────────────
    await message.reply(
        file=discord.File(output_bytes, filename=filename)
    )

    # ── Forward to 4K channel ─────────────────────────
    four_k_channel_id = await get_4k_channel_id(message)

    output_bytes.seek(0)  # Reset buffer position before sending to another channel

    if four_k_channel_id:
        channel = message.guild.get_channel(four_k_channel_id)

        if channel:
            
            content = (
                f"📸 {message.author.mention} caught {replied.author.mention} in 4K\n\n"
                f"{replied.jump_url}"
            )

            embed = discord.Embed(
                title="4K Alert!",
                description=content,
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Original message by {replied.author.display_name}", icon_url=replied.author.display_avatar.url)
    

            await channel.send(
                embed=embed,
                file=discord.File(output_bytes, filename=filename)
            )

            

    await bot.process_commands(message)
