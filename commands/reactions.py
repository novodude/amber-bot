import discord
from discord import Color, app_commands
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
    },
    'yeet': {
        'act': 'yeeted',
        'color': discord.Color.dark_purple(),
        'emoji': '🥏',
        'lone': False,
        'link': '',
        'desc_everyone': 'bye bye everyone >:3',
        'desc_self': 'weeee',
        'desc_other': 'can {user.display_name} fly?'
    },
    'facepalm': {
        'act': 'facepalms',
        'color': discord.Color.dark_orange(),
        'emoji': '🤦',
        'lone': True,
        'link': 'at',
        'desc_everyone': '*sigh* so uh why we facepalming?',
        'desc_self': "it's okay to be embarrassed *pat*",
        'desc_other': 'you made {author.display_name} facepalm ._.'
    },
    'baka': {
        'act': 'stoopid',
        'color': discord.Color.brand_green(),
        'emoji': '🦆',
        'lone': False,
        'link': ['said', 'is'],
        'desc_everyone': '{author.display_name} included :P',
        'desc_self': "mybe you're but you are the special kind of stoopid :3",
        'desc_other': '{author.display_name} said that not me ._.'
    }
}
REACTION = {
    'blush': {
        'title': '{author.display_name} is blushing',
        'description': 'awww how cute',
        'color': discord.Color.pink()
    },
    'shrug': {
        'title': '{author.display_name} shrugs',
        'description': 'shrugs like a rug',
        'color': discord.Color.dark_purple()
    },
    'yawn': {
        'title': '{author.display_name} yawned',
        'description': 'eppy {author.display_name} *pet*',
        'color': discord.Color.pink()
    },
    'angry': {
        'title': '{author.display_name} is angy >:(',
        'description': 'be careful everyone',
        'color': discord.Color.red()
    },
    'bored': {
        'title': '{author.display_name} is bored to the bone',
        'description': 'bored? do a backflip :D!',
        'color': discord.Color.gold()

    },
    'happy': {
        'title': '{author.display_name} is happy :3',
        'description': 'yayyy - happy for you too',
        'color': discord.Color.yellow()
    },
    'nope': {
        'title': '{author.display_name} noped out of here',
        'description': 'nope nah nuh uh never :P',
        'color': discord.Color.brand_green()
    }
}


def build_title(action: str, action_data: dict, author_name: str, target_name: str = None, everyone: bool = False) -> str:
    emoji = action_data['emoji']
    act = action_data['act']
    link = action_data['link']
    
    if action == 'baka':
        if everyone:
            return f"**{emoji} {author_name} {link[0]} everyone {link[1]} {act} {emoji}**"
        elif not target_name:
            return f"**{emoji} {author_name} {link[0]} {act} {emoji}**"
        elif target_name == author_name:
            return f"**{emoji} {author_name} {link[1]} {act} {emoji}**"
        else:
            return f"**{emoji} {author_name} {link[0]} {target_name} {link[1]} {act} {emoji}**"
    
    if everyone:
        if action_data['lone']:
            return f"**{emoji} {author_name} {act} {link} everyone {emoji}**"
        return f"**{emoji} {author_name} {act} everyone {emoji}**"
    
    if not target_name or target_name == author_name:
        if action_data['lone']:
            return f"**{emoji} {author_name} {act} {link} themselves {emoji}**"
        return f"**{emoji} {author_name} {act} themselves {emoji}**"
    
    if action_data['lone']:
        return f"**{emoji} {author_name} {act} {link} {target_name} {emoji}**"
    return f"**{emoji} {author_name} {act} {target_name} {emoji}**"





async def setup_reactions(bot):
    # the all mighty /do command(first command i coded :P)
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
            'smile', 'wave', 'laugh', 'yeet',
            'baka', 'facepalm', 'think'
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
            
            target_name = user.display_name if user else None
            embed.title = build_title(action, action_data, interaction.user.display_name, target_name, everyone)
            
            if everyone:
                embed.description = action_data['desc_everyone'].format(user=interaction.user, author=interaction.user)
            elif user and user == interaction.user:
                embed.description = action_data['desc_self'].format(user=interaction.user, author=interaction.user)
            elif user:
                embed.description = action_data['desc_other'].format(user=user, author=interaction.user)
            else:
                embed.description = action_data['desc_self'].format(user=interaction.user, author=interaction.user)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

# /look commmand
    @bot.tree.command(name="look", description="Give a reaction with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(reaction="Choose an reaction to perform")
    async def do_reaction(
        interaction: discord.Interaction,
        reaction: Literal['blush', 'shrug', 'yawn', 'angry', 'bored', 'happy', 'nope']
    ):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://nekos.best/api/v2/{reaction}") as response:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
            reaction_data = REACTION[reaction]
            embed = discord.Embed(color=reaction_data['color'])
            embed.set_image(url=gif_url)
            embed.title = reaction_data['title'].format(author=interaction.user)
            embed.description = reaction_data['description'].format(author=interaction.user)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="**Error**",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
