import discord
from discord import app_commands
import aiohttp
from typing import Optional, Literal

ACTIONS = {
    'hug': {
        'description': 'hugs',
        'color': discord.Color.red(),
        'emoji': '🤗'
    },
    'kiss': {
        'description': 'kisses',
        'color': discord.Color.pink(),
        'emoji': '😘'
    },
    'pat': {
        'description': 'pats',
        'color': discord.Color.blue(),
        'emoji': '🫳'
    },
    'slap': {
        'description': 'slaps',
        'color': discord.Color.orange(),
        'emoji': '👋'
    },
    'poke': {
        'description': 'pokes',
        'color': discord.Color.green(),
        'emoji': '👉'
    },
    'cuddle': {
        'description': 'cuddles with',
        'color': discord.Color.purple(),
        'emoji': '🫂'
    },
    'bite': {
        'description': 'bites',
        'color': discord.Color.red(),
        'emoji': '😬'
    },
    'kick': {
        'description': 'kicks',
        'color': discord.Color.orange(),
        'emoji': '🦵'
    },
    'punch': {
        'description': 'punches',
        'color': discord.Color.red(),
        'emoji': '👊'
    },
    'tickle': {
        'description': 'tickles',
        'color': discord.Color.yellow(),
        'emoji': '🤭'
    },
    'feed': {
        'description': 'feeds',
        'color': discord.Color.green(),
        'emoji': '🍰'
    },
    'highfive': {
        'description': 'high-fives',
        'color': discord.Color.gold(),
        'emoji': '✋'
    },
    'dance': {
        'description': 'is dancing',
        'color': discord.Color.purple(),
        'emoji': '💃'
    },
    'sleep': {
        'description': 'is sleeping',
        'color': discord.Color.dark_grey(),
        'emoji': '😴'
    },
    'cry': {
        'description': 'is crying',
        'color': discord.Color.blue(),
        'emoji': '😢'
    },
    'blush': {
        'description': 'is blushing',
        'color': discord.Color.pink(),
        'emoji': '😊'
    },
    'smile': {
        'description': 'is smiling',
        'color': discord.Color.gold(),
        'emoji': '😊'
    },
    'think': {
        'description': 'is thinking',
        'color': discord.Color.teal(),
        'emoji': '🤔'
    },
    'shrug': {
        'description': 'shrugs',
        'color': discord.Color.greyple(),
        'emoji': '🤷'
    },
    'yawn': {
        'description': 'yawns',
        'color': discord.Color.orange(),
        'emoji': '🥱'
    },
    'wave': {
        'description': 'waves',
        'color': discord.Color.green(),
        'emoji': '👋'
    },
    'laugh': {
        'description': 'is laughing',
        'color': discord.Color.yellow(),
        'emoji': '😂'
    }
}

async def setup_reactions(bot):
    """Setup the /do command with all reactions"""
    
    @bot.tree.command(name="do", description="Perform an action with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(
        action="Choose an action to perform",
        user="The person you want to interact with (optional)"
    )
    async def do_action(
        interaction: discord.Interaction,
        action: Literal[
            'hug', 'kiss', 'pat', 'slap', 'poke', 'cuddle', 'bite', 'kick',
            'punch', 'tickle', 'feed', 'highfive', 'dance', 'sleep', 'cry',
            'blush', 'smile', 'think', 'shrug', 'yawn', 'wave', 'laugh'
        ],
        user: Optional[discord.User] = None
    ):
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://nekos.best/api/v2/{action}") as response:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
            action_data = ACTIONS[action]            
            embed = discord.Embed(color=action_data['color'])
            embed.set_image(url=gif_url)
            if user and user != interaction.user:
                embed.description = f"{interaction.user.mention} {action_data['description']} {user.mention} {action_data['emoji']}"
            elif user == interaction.user:
                embed.description = f"{interaction.user.mention} {action_data['description']} themselves {action_data['emoji']}"
            else:
                embed.description = f"{interaction.user.mention} {action_data['description']} {action_data['emoji']}"
            
            await interaction.followup.send(embed=embed)           
        except Exception as e:
            await interaction.followup.send(f"Oops! Something went wrong: {e}", ephemeral=True)