# other libraries
import os
import logging
import re
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
from commands.banking import banking_setup, message_xp_handler
from commands.moderation import moderation_setup
from commands.helper import help_setup
from commands.mimic import mimic_setup
from commands.pet import pet_setup
from commands.shop import shop_setup
# databases
from utils.radio.database import init_radio_db
from utils.userbase.database import init_user_db
from utils.quests import message_quest_handler
from utils.pet import touch_owner_activity
from utils.economy import get_user_id_from_discord

load_dotenv()
token = os.getenv("DISCORD_TOKEN")


async def get_prefix(bot, message):
    if not message.guild:
        return "!"
    async with aiosqlite.connect("data/user.db") as db:
        cursor = await db.execute(
            "SELECT prefix FROM guild_config WHERE guild_id = ?", (message.guild.id,)
        )
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
    await bot.load_extension('commands.quests')


@bot.event
async def on_ready():
    print(f"we are quacking here, {bot.user.name}")
    await init_user_db()
    await init_radio_db()
    await setup_reactions(bot)
    await melody_setup(bot)
    await fun_setup(bot)
    await minigames_setup(bot)
    await banking_setup(bot)
    await moderation_setup(bot)
    await utils_setup(bot)
    await help_setup(bot)
    await mimic_setup(bot)
    await pet_setup(bot)
    await shop_setup(bot)
    await load_extensions()
    await bot.tree.sync()
    print("Commands synced.")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await handle_4k(bot, message)
    await handle_pin(bot, message)
    await message_xp_handler(message)
    await message_quest_handler(message)

    # Update pet inactivity timer whenever the owner sends any message
    user_id = await get_user_id_from_discord(message.author.id)
    if user_id:
        await touch_owner_activity(user_id)

    mimic_cog = bot.get_cog("Mimic")
    if mimic_cog:
        await mimic_cog.handle_mimic(message)

    await bot.process_commands(message)


@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")


bot.run(token, reconnect=True, log_handler=handler)
