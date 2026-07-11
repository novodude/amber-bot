# other libraries
import os
import logging
import aiosqlite
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
from commands.animals import animal_setup
from commands.image import image_setup
from commands.anime import anime_setup
from commands.leaderboard import leaderboard_setup
from commands.user import user_setup
from commands.amber import amber_setup
from commands.owner import owner_setup, updates_handler
from commands.art import art_setup
from commands.lunita_bridge import setup_lunita_bridge
try:
    from commands.debugging import debug_setup
except ImportError:
    pass
# databases
from utils.art.art import ArtUtils
from utils.radio.database import init_radio_db
from utils.userbase.database import init_user_db
from utils.userbase.owner import init_owner_db
from utils.quests import message_quest_handler
from utils.pet import touch_owner_activity
from utils.userbase.database import get_user_id_from_discord
from utils.amber import amber_handler, handle_delete_reply

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
    await bot.load_extension('commands.radio')
    await bot.load_extension('commands.quests')


@bot.event
async def on_ready():
    print(f"we are quacking here, {bot.user.name}")
    await init_user_db()
    await init_radio_db()
    await init_owner_db()
    await amber_setup(bot)
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
    await animal_setup(bot)
    await image_setup(bot)
    await anime_setup(bot)
    await owner_setup(bot)
    await art_setup(bot)
    await setup_lunita_bridge(bot)
    try:        await debug_setup(bot)
    except NameError: pass
    await leaderboard_setup(bot)
    await user_setup(bot)
    await load_extensions()
    await bot.tree.sync()
    print("Commands synced.")


LUNITA_BOT_ID = 951539463224451102

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        # Skip all the human-facing stuff (AI replies, xp, quests, etc.) for
        # any bot — but let Lunita specifically still trigger prefix commands
        # like !do / !look / !rate. Gated by ID so a random bot can't abuse
        # the dabloon-rewarding action commands.
        if message.author.id == LUNITA_BOT_ID:
            await bot.process_commands(message)
        return

    await handle_4k(bot, message)
    await handle_pin(message)
    await message_xp_handler(message)
    await message_quest_handler(message)
    await updates_handler(bot, message)
    await handle_delete_reply(bot, message)
    await amber_handler(bot, message)

    user_id = await get_user_id_from_discord(message.author.id)
    if user_id:
        await touch_owner_activity(user_id)

    mimic_cog = bot.get_cog("Mimic")
    if mimic_cog:
        await mimic_cog.handle_mimic(message)

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    print(f"[command error] {ctx.command}: {error!r}")
    if isinstance(error, commands.CommandNotFound):
        return  # comment this back in once we confirm commands are registering
    await ctx.send(f"-# something broke: `{error}`")


@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")


bot.run(token, reconnect=True, log_handler=handler)
