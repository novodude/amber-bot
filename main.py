import discord
from discord.ext import commands
from discord import app_commands, User
import logging
from dotenv import load_dotenv
import os
from commands.reactions import setup_reactions
from commands.inkblot import inkblot_setup
import random
import aiohttp

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
    await bot.tree.sync()
    print("Commands synced.")

@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):   
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")

@bot.tree.command(name="duck", description="Get a random duck GIF.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def duck(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://random-d.uk/api/v2/list") as resp:
            data = await resp.json()
            gifs = data.get("gifs", [])
            if gifs:
                random_gif = random.choice(gifs)
                gif_url = f"https://random-d.uk/api/{random_gif}"
            else:
                gif_url = "https://random-d.uk/api/random"
    
    embed = discord.Embed(title="Random Duck!")
    embed.set_image(url=gif_url)
    await interaction.response.send_message(embed=embed)
bot.run(token, log_handler=handler, log_level=logging.DEBUG)