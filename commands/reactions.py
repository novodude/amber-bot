import discord
from discord import app_commands
import aiohttp
from typing import Optional, Literal

ACTIONS = {
    'hug': {
        'description': 'hugs',
        'color': discord.Color.red(),
        'emoji': '🤗',
        'lone': False,
        'link': ''
    },
    'kiss': {
        'description': 'kisses',
        'color': discord.Color.pink(),
        'emoji': '😘',
        'lone': False,
        'link': ''
    },
    'pat': {
        'description': 'pats',
        'color': discord.Color.blue(),
        'emoji': '🫳',
        'lone': False,
        'link': ''
    },
    'slap': {
        'description': 'slaps',
        'color': discord.Color.orange(),
        'emoji': '👋',
        'lone': False,
        'link': ''
    },
    'poke': {
        'description': 'pokes',
        'color': discord.Color.green(),
        'emoji': '👉',
        'lone': False,
        'link': ''
    },
    'cuddle': {
        'description': 'cuddles with',
        'color': discord.Color.purple(),
        'emoji': '🫂',
        'lone': False,
        'link': 'with'
    },
    'bite': {
        'description': 'bites',
        'color': discord.Color.red(),
        'emoji': '😬',
        'lone': False,
        'link': ''
    },
    'kick': {
        'description': 'kicks',
        'color': discord.Color.orange(),
        'emoji': '🦵',
        'lone': False,
        'link': ''
    },
    'punch': {
        'description': 'punches',
        'color': discord.Color.red(),
        'emoji': '👊',
        'lone': False,
        'link': ''
    },
    'tickle': {
        'description': 'tickles',
        'color': discord.Color.yellow(),
        'emoji': '🤭',
        'lone': False,
        'link': ''
    },
    'feed': {
        'description': 'feeds',
        'color': discord.Color.green(),
        'emoji': '🍰',
        'lone': False,
        'link': ''
    },
    'highfive': {
        'description': 'high-fives',
        'color': discord.Color.gold(),
        'emoji': '✋',
        'lone': False,
        'link': ''
    },
    'dance': {
        'description': 'is dancing',
        'color': discord.Color.purple(),
        'emoji': '💃',
        'lone': True,
        'link': 'with'
    },
    'sleep': {
        'description': 'is sleeping',
        'color': discord.Color.dark_grey(),
        'emoji': '😴',
        'lone': True,
        'link': 'with'
    },
    'cry': {
        'description': 'is crying',
        'color': discord.Color.blue(),
        'emoji': '😢',
        'lone': True,
        'link': 'with'
    },
    'blush': {
        'description': 'is blushing',
        'color': discord.Color.pink(),
        'emoji': '😊',
        'lone': True,
        'link': 'at'
    },
    'smile': {
        'description': 'is smiling',
        'color': discord.Color.gold(),
        'emoji': '😊',
        'lone': True,
        'link': 'at'
    },
    'think': {
        'description': 'is thinking',
        'color': discord.Color.teal(),
        'emoji': '🤔',
        'lone': True,
        'link': 'about'
    },
    'shrug': {
        'description': 'shrugs',
        'color': discord.Color.greyple(),
        'emoji': '🤷',
        'lone': True,
        'link': 'at'
    },
    'yawn': {
        'description': 'yawns',
        'color': discord.Color.orange(),
        'emoji': '🥱',
        'lone': True,
        'link': 'with'
    },
    'wave': {
        'description': 'waves',
        'color': discord.Color.green(),
        'emoji': '👋',
        'lone': True,
        'link': 'at'
    },
    'laugh': {
        'description': 'is laughing',
        'color': discord.Color.yellow(),
        'emoji': '😂',
        'lone': True,
        'link': 'with'
    }
}


async def setup_reactions(bot):
    @bot.tree.command(name="do", description="Perform an action with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(
        action="Choose an action to perform",
        user="The person you want to interact with (optional)",
        everyone="Perform the action on everyone (optional)"
    )
    async def do_action(
        interaction: discord.Interaction,
        action: Literal[
            'hug', 'kiss', 'pat', 'slap', 'poke', 'cuddle', 'bite', 'kick',
            'punch', 'tickle', 'feed', 'highfive', 'dance', 'sleep', 'cry',
            'blush', 'smile', 'think', 'shrug', 'yawn', 'wave', 'laugh'
        ],
        user: Optional[discord.User] = None,
        everyone: Optional[bool] = False
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
                if action_data['lone']:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"{action_data['link']} {user.mention} {action_data['emoji']}"
                    )
                else:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"{user.mention} {action_data['emoji']}"
                    )
            
            elif user == interaction.user:
                if action_data['lone']:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"{action_data['link']} themselves {action_data['emoji']}"
                    )
                else:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"themselves {action_data['emoji']}"
                    )
            
            elif everyone == True:
                if action_data['lone']:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"{action_data['link']} everyone {action_data['emoji']}"
                    )
                else:
                    embed.description = (
                        f"{interaction.user.mention} {action_data['description']} "
                        f"everyone {action_data['emoji']}"
                    )
            
            else:
                embed.description = (
                    f"{interaction.user.mention} {action_data['description']} "
                    f"{action_data['emoji']}"
                )
                       
            await interaction.followup.send(embed=embed)           
        except Exception as e:
            embed = discord.Embed(
                title="error",
                description="somthing went wrong!",
                color=discord.Color.red()
            )
            await interaction.followup.send (embed=embed, ephemeral=True)