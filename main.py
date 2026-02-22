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
        "- `/do`: do an action with anime gifs. UwU\n"
        "- `/look`: do a reaction with anime gifs. >:3\n"
        "- `/rarch`: Generate a random rorschach test. o_o\n"
        "- `/ofc`: Careful with the out of context command, it can hurt. .-.\n"
        "- `/misquote`: spread misinformation in someone's name. :D\n"
        "- `/melody`: Generate a melody. :P\n"
        "- `/ping`: Check the bot's latency. :D\n"
    )

    radio = (
        "- `/radio`: Play your radio playlist or public playlists. :>\n"
        "- `/radio_set`: Create a new radio playlist. \n"
        "- `/radio_libraries`: View your radio playlists. \n"
        "- `/radio_remove`: Delete a radio playlist. >:D\n"
        "- `/radio_stop`: Stop the radio and disconnect. :D\n"
        "- `radio_sync`: Sync your radio playlist. :P\n"
    )

    games = (
        "- `/game tic_tac_toe`: play tic tac toe against AI to gain dabloons\n"
        "- `/game duck_clicker`: like cookie clicker, tap 5 time to gain **2** dabloons\n"
    )

    bot_events = (
        "keep in mind amber has to be in the server to do these"
        "- reply to a message with `4k` and you will quote it in 4k. :3\n"
        "- you can pin or unpin messages by replying to them with `pin` or `unpin`. >:P\n"
    )
 
    embed = discord.Embed(title="Quack! Here are some commands you can use:", color=discord.Color.gold())
    embed.add_field(name="Cute Feathered and Furry Friends", value=animals, inline=False)
    embed.add_field(name="Fun", value=games_n_reactions, inline=False)
    embed.add_field(name="Games", value=games, inline=False)
    embed.add_field(name="Radio System", value=radio, inline=False)
    embed.add_field(name="Bot Events", value=bot_events, inline=False)
    embed.set_footer(text="OFC quotes from AMTA discord server 💜")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ping(interaction: discord.Interaction):   
    latency = bot.latency * 1000
    await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")

bot.run(token, reconnect=True, log_handler=handler)
