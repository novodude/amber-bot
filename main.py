# other libraries
import os
import logging
import aiosqlite
from io import BytesIO
from dotenv import load_dotenv
# discord library
import discord
from discord.ext import commands
from discord import app_commands
# commands and scripts
from commands.reactions import setup_reactions
from commands.fun import fun_setup, handle_4k
from commands.melody import melody_setup
from commands.minigames import minigames_setup
from commands.utils import utils_setup, handle_pin
from commands.banking.banking import banking_setup
from commands.moderation import moderation_setup
from commands.helper import help_setup
# databases
from utils.radio.database import init_radio_db
from utils.userbase.database import init_user_db

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
  

async def get_prefix(bot, message):
    if not message.guild:
        return "!"
    
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute("SELECT prefix FROM guild_config WHERE guild_id = ?", (message.guild.id,))
        row = await cursor.fetchone()
        return row[0] if row else "!"


handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

async def load_extensions():
    await bot.load_extension('commands.radio.settings')
    await bot.load_extension('commands.radio.player')

@bot.event
async def on_ready():
    print(f"we are quacking here, {bot.user.name}")
    await setup_reactions(bot)
    await melody_setup(bot)
    await fun_setup(bot)
    await minigames_setup(bot)
    await banking_setup(bot)
    await moderation_setup(bot)
    await utils_setup(bot)
    await help_setup(bot)
    await init_user_db()
    await init_radio_db()
    await load_extensions()
    await bot.tree.sync()
    print("Commands synced.")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if await handle_4k(bot, message):
        return
    if await handle_pin(bot, message):
        return
    await bot.process_commands(message)

@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):   
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")

bot.run(token, reconnect=True, log_handler=handler)
