import discord
from discord import app_commands
import aiohttp
from typing import Optional, Literal

ACTIONS = {
    'hug': {
        'act': 'hugs',
        'color': discord.Color.red(),
        'emoji': '🤗',
        'lone': False,
        'link': '',
        'desc_everyone': 'group hug time!',
        'desc_self': 'awww self-love is important 🤍',
        'desc_other': 'so sweet!'
    },
    'kiss': {
        'act': 'kisses',
        'color': discord.Color.pink(),
        'emoji': '💓',
        'lone': False,
        'link': '',
        'desc_everyone': 'lots of love to go around!',
        'desc_self': 'self-love is the best love! 💖',
        'desc_other': 'my heart is melting 🥺'
    },
    'pat': {
        'act': 'pats',
        'color': discord.Color.blue(),
        'emoji': '🫳',
        'lone': False,
        'link': '',
        'desc_everyone': 'PAT PAT PAT',
        'desc_self': 'cute pet for me 🥰',
        'desc_other': 'how adorable!'
    },
    'slap': {
        'act': 'slaps',
        'color': discord.Color.orange(),
        'emoji': '👋',
        'lone': False,
        'link': '',
        'desc_everyone': 'someone needs to calm down!',
        'desc_self': 'hug them people, someone need love!',
        'desc_other': 'this hurts!'
    },
    'poke': {
        'act': 'pokes',
        'color': discord.Color.green(),
        'emoji': '👉',
        'lone': False,
        'link': '',
        'desc_everyone': 'hehe >:3',
        'desc_self': 'poking yourself? okay then :P',
        'desc_other': 'hey {user.display_name} poke em back >:3'
    },
    'cuddle': {
        'act': 'cuddles with',
        'color': discord.Color.purple(),
        'emoji': '🫂',
        'lone': False,
        'link': 'with',
        'desc_everyone': 'group cuddle time!',
        'desc_self': 'so cute cuddling with myself :3',
        'desc_other': 'so warm and fuzzy!'
    },
    'bite': {
        'act': 'bites',
        'color': discord.Color.red(),
        'emoji': '😬',
        'lone': False,
        'link': '',
        'desc_everyone': 'someone is feeling feisty!',
        'desc_self': 'that hurts! why would you bite yourself?!',
        'desc_other': 'ouch! that must have hurt!'
    },
    'kick': {
        'act': 'kicks',
        'color': discord.Color.orange(),
        'emoji': '🦵',
        'lone': False,
        'link': '',
        'desc_everyone': 'how rude! >:(',
        'desc_self': 'give them some cuddles everyone! :3',
        'desc_other': 'nyahahaha take that! >:D'
    },
    'punch': {
        'act': 'punches',
        'color': discord.Color.red(),
        'emoji': '👊',
        'lone': False,
        'link': '',
        'desc_everyone': 'punch for you and you and you-!',
        'desc_self': 'go rest and relax, no need to punch yourself :(',
        'desc_other': 'one punch coming right up!'
    },
    'tickle': {
        'act': 'tickles',
        'color': discord.Color.yellow(),
        'emoji': '🤭',
        'lone': False,
        'link': '',
        'desc_everyone': 'tickle fight everyone! :D',
        'desc_self': 'that doesnt work on yourself silly :P',
        'desc_other': 'wanna hear you laugh! hehe :3'
    },
    'feed': {
        'act': 'feeds',
        'color': discord.Color.green(),
        'emoji': '🍰',
        'lone': False,
        'link': '',
        'desc_everyone': 'how about some treats for everyone! :3',
        'desc_self': 'self-care is important, enjoy your treat! 🍩',
        'desc_other': 'gonna get you chonky! hehe :P'
    },
    'highfive': {
        'act': 'high-fives',
        'color': discord.Color.gold(),
        'emoji': '✋',
        'lone': False,
        'link': '',
        'desc_everyone': 'team spirit! high five everyone! 🙌',
        'desc_self': 'clapping for yourself! you deserve it! 👏',
        'desc_other': 'nice one! *slap* 🙌'
    },
    'dance': {
        'act': 'is dancing',
        'color': discord.Color.purple(),
        'emoji': '💃',
        'lone': True,
        'link': 'with',
        'desc_everyone': 'dance party time! 🕺💃',
        'desc_self': 'dancing like nobody is watching! :D',
        'desc_other': 'look at those moves! :3'
    },
    'sleep': {
        'act': 'is sleeping',
        'color': discord.Color.dark_grey(),
        'emoji': '😴',
        'lone': True,
        'link': 'with',
        'desc_everyone': 'everyone nap time! *zzz*',
        'desc_self': 'sweet dreams! 💤',
        'desc_other': 'shhh, let them rest! 🤫'
    },
    'cry': {
        'act': 'is crying',
        'color': discord.Color.blue(),
        'emoji': '😢',
        'lone': True,
        'link': 'with',
        'desc_everyone': 'group hug for the tears! 🫂',
        'desc_self': 'aww {user.display_name} is lonely\n its okay to cry, let it out 💙',
        'desc_other': 'aww dont cry! *hugs* 🥺'
    },
    'blush': {
        'act': 'is blushing',
        'color': discord.Color.pink(),
        'emoji': '😊',
        'lone': True,
        'link': 'at',
        'desc_everyone': 'aww give them some space everyone',
        'desc_self': 'aww getting all flustered! 😊',
        'desc_other': 'hehe so cute when you blush! :3'
    },
    'smile': {
        'act': 'is smiling',
        'color': discord.Color.gold(),
        'emoji': '😊',
        'lone': True,
        'link': 'at',
        'desc_everyone': 'smiles all around! :D',
        'desc_self': 'that smile looks good on you! 😄',
        'desc_other': 'your smile is contagious! 😊'
    },
    'think': {
        'act': 'is thinking',
        'color': discord.Color.teal(),
        'emoji': '🤔',
        'lone': True,
        'link': 'about',
        'desc_everyone': 'I wonder what the others are up to?',
        'desc_self': 'hmm what could it be? 🤔',
        'desc_other': 'they do that all day btw :3'
    },
    'shrug': {
        'act': 'shrugs',
        'color': discord.Color.greyple(),
        'emoji': '🤷',
        'lone': True,
        'link': 'at',
        'desc_everyone': 'nobody knows!',
        'desc_self': 'meh, who knows? 🤷',
        'desc_other': 'idk either tbh :P'
    },
    'yawn': {
        'act': 'yawns',
        'color': discord.Color.orange(),
        'emoji': '🥱',
        'lone': True,
        'link': 'with',
        'desc_everyone': 'yawns are contagious! *yawn* 🥱',
        'desc_self': 'sleepy time? get some rest! 😴',
        'desc_other': 'tired already? hehe :3'
    },
    'wave': {
        'act': 'waves',
        'color': discord.Color.green(),
        'emoji': '👋',
        'lone': True,
        'link': 'at',
        'desc_everyone': 'hello everyone! 👋✨',
        'desc_self': 'hello me :D\n waving at the mirror? silly! :P',
        'desc_other': 'wave back! dont be shy! :3'
    },
    'laugh': {
        'act': 'is laughing',
        'color': discord.Color.yellow(),
        'emoji': '😂',
        'lone': True,
        'link': 'with',
        'desc_everyone': 'everyone is laughing! what a mood! :P',
        'desc_self': 'having a good time! keep it up! :D',
        'desc_other': 'haha your laugh is adorable! :3'
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
            if everyone:
                # Everyone case
                if action_data['lone']:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} {action_data['link']} everyone {action_data['emoji']}**"
                else:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} everyone {action_data['emoji']}**"
                embed.description = action_data['desc_everyone'].format(user=interaction.user)
            elif user and user == interaction.user:
                # Self-targeting case
                if action_data['lone']:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} {action_data['link']} themselves {action_data['emoji']}**"
                else:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} themselves {action_data['emoji']}**"
                embed.description = action_data['desc_self'].format(user=interaction.user)
            elif user:
                # Targeting another user
                if action_data['lone']:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} {action_data['link']} {user.display_name} {action_data['emoji']}**"
                else:
                    embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} {user.display_name} {action_data['emoji']}**"
                embed.description = action_data['desc_other'].format(user=user, author=interaction.user)
            else:
                # No target (solo action)
                embed.title = f"**{action_data['emoji']} {interaction.user.display_name} {action_data['act']} {action_data['emoji']}**"
                embed.description = action_data['desc_self'].format(user=interaction.user)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
