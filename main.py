import os
import discord
import logging
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from commands.reactions import setup_reactions
from commands.inkblot import inkblot_setup
from commands.ofc import ofc_setup
from commands.animals import animals_setup
from commands.fun import fun_setup, register_events
from commands.melody import melody_setup
from pathlib import Path


load_dotenv()
token = os.getenv("DISCORD_TOKEN")
  
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"we are quacking here, {bot.user.name}")
    await setup_reactions(bot)
    await inkblot_setup(bot)
    await ofc_setup(bot)
    await animals_setup(bot)
    await melody_setup(bot)
    await fun_setup(bot)
    await register_events(bot)
    await bot.tree.sync()
    print("Commands synced.")
@bot.event
async def on_guild_join(guild):
        general = discord.utils.find(lambda x: x.name == 'general' and x.type == discord.ChannelType.text, guild.channels)
        if general and general.permissions_for(guild.me).send_messages:
            await general.send("Quack! Thanks for adding me to your server!")

@bot.tree.command(name="help", description="Get a list of available commands.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def help_command(interaction: discord.Interaction):
    animals = (
        "- `/cat`: Get a random cute cat image. :3\n"
        "- `/duck`: Get a random mighty duck image. >:P\n"
        "- `/rat`: Get a random adorable rat image. ^_^\n\n"
    )
    games_n_reactions = (
        "- `/rarch`: Generate a random rorschach test. o_o\n"
        "- `/ofc`: Careful with the out of context command, it can hurt. .-.\n"
        "- `/do`: Anime reaction images for various moods. UwU\n"
    )
 
    embed = discord.Embed(title="Quack! Here are some commands you can use:", color=discord.Color.gold())
    embed.add_field(name="Cute Feathered and Furry Friends", value=animals, inline=False)
    embed.add_field(name="Games and Fun", value=games_n_reactions, inline=False)
    embed.set_footer(text="OFC quotes from AMTA discord server 💜")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):   
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")






bot.run(token, reconnect=True, log_handler=handler)
