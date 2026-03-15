from discord import Color, app_commands, user
from typing import Optional, Literal
import discord
from datetime import datetime
import aiohttp
import random

from utils.userbase.ensure_registered import ensure_registered
from utils.action_counts import (
    increment_action_count,
    maybe_reward_dabloons,
)

# ── Action definitions ────────────────────────────────────────────────────────
# Each action has:
#   act          - verb used in the embed title
#   color        - embed sidebar color
#   emoji        - displayed in title and button
#   lone         - if True, action can be done alone (uses 'link' when paired)
#   link         - preposition used between actor and target (e.g. "with", "at")
#                  baka uses a list: [verb for others, verb for self]
#   desc_everyone - list of descriptions when targeting everyone
#   desc_self     - list of descriptions when targeting yourself
#   desc_other    - list of descriptions when targeting another user
#                  supports {user} and {author} format placeholders
#                  one entry is chosen randomly on each use
#
#   Counter text format:
#     kiss        → private: "{author} kissed {user} {n} times"
#     all others  → public:  "{user} got hugged {n} times"
ACTIONS = {
    'hug': {
        'act': 'hugs',
        'color': discord.Color.red(),
        'emoji': '🤗',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'group hug time!',
            'spreading the love to everyone! 🤗',
            'everyone gets a hug today! 💞',
            'arms wide open for all! 🫂',
        ],
        'desc_self': [
            'awww self-love is important 🤍',
            'hugging yourself is valid! 🥰',
            'self-care moment right there 💙',
            'you deserve all the hugs! 🤗',
        ],
        'desc_other': [
            'so sweet!',
            'awww how wholesome 🥺',
            'that hug looks so warm! 🤍',
            '{user.display_name} needed that :3',
            'best hugger in the server! 🤗',
        ],
    },
    'kiss': {
        'act': 'kisses',
        'color': discord.Color.pink(),
        'emoji': '💓',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'lots of love to go around!',
            'kisses for everyone! 💋',
            'spreading the smooches! 😘',
            'mwah mwah mwah all around! 💓',
        ],
        'desc_self': [
            'self-love is the best love! 💖',
            'kiss yourself, you deserve it! 😘',
            'loving yourself first 💓',
            'the most important kiss of all 💕',
        ],
        'desc_other': [
            'my heart is melting 🥺',
            'awww so cute!! 💓',
            'ooh la la~ 😘',
            '{user.display_name} is blushing for sure 💕',
            'too adorable!! 🥰',
        ],
    },
    'pat': {
        'act': 'pats',
        'color': discord.Color.blue(),
        'emoji': '🫳',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'PAT PAT PAT',
            'pat patrol is here! 🫳',
            'everyone gets a head pat! ✨',
            'pat pat pat for all~ 💙',
        ],
        'desc_self': [
            'cute pet for me 🥰',
            'patting yourself takes skill :P',
            'self-pat! you did great today 🫳',
            'good job you! *pat pat* ✨',
        ],
        'desc_other': [
            'how adorable!',
            '*pat pat pat* 🥰',
            '{user.display_name} has been blessed with pats ✨',
            'best pats in the server! 🫳',
            'so gentle so sweet~ 💙',
        ],
    },
    'poke': {
        'act': 'pokes',
        'color': discord.Color.green(),
        'emoji': '👉',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'hehe >:3',
            'poke poke poke everyone! 👉',
            'nobody is safe from the pokes! >:3',
            'poking spree activated 😈',
        ],
        'desc_self': [
            'poking yourself? okay then :P',
            'boop! self-poke achieved 👉',
            'why tho :P',
            'you just poked yourself lol',
        ],
        'desc_other': [
            'hey {user.display_name} poke em back >:3',
            'gotcha! 👉',
            'poke received, poke back? :P',
            '{user.display_name} has been poked! >:3',
            '*sneaky poke* hehe',
        ],
    },
    'cuddle': {
        'act': 'cuddles with',
        'color': discord.Color.purple(),
        'emoji': '🫂',
        'lone': False,
        'link': 'with',
        'desc_everyone': [
            'group cuddle time!',
            'pile up everyone! 🫂',
            'cuddle puddle activated 💜',
            'warmest moment of the day 🥰',
        ],
        'desc_self': [
            'so cute cuddling with myself :3',
            'solo cuddle session! 💜',
            'hugging a pillow counts too! 🫂',
            'cozy and comfy all by yourself :3',
        ],
        'desc_other': [
            'so warm and fuzzy!',
            'the coziest duo 🫂',
            'awww so sweet 💜',
            '{user.display_name} looks so comfy right now 🥰',
            'cuddle level: maximum 💜',
        ],
    },
    'bite': {
        'act': 'bites',
        'color': discord.Color.red(),
        'emoji': '😬',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'someone is feeling feisty!',
            'chomp chomp chomp everyone! 😬',
            'nobody is safe! >:3',
            'watch your fingers everyone!',
        ],
        'desc_self': [
            'that hurts! why would you bite yourself?!',
            'ow ow ow!! D:',
            'please dont do that!! 😬',
            'seeking attention in strange ways huh :P',
        ],
        'desc_other': [
            'ouch! that must have hurt!',
            'CHOMP! 😬',
            '{user.display_name} has been bitten! >:3',
            'feisty today arent we! 😤',
            'did {user.display_name} deserve that? probably :P',
        ],
    },
    'kick': {
        'act': 'kicks',
        'color': discord.Color.orange(),
        'emoji': '🦵',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'how rude! >:(',
            'mass kicking spree! 🦵',
            'everyone gets a kick! how generous :P',
            'clear the room! 😤',
        ],
        'desc_self': [
            'give them some cuddles everyone! :3',
            'self-kick? that takes talent 🦵',
            'are you okay?? 😟',
            'someone needs a hug instead :(',
        ],
        'desc_other': [
            'nyahahaha take that! >:D',
            'BOOT! 🦵',
            '{user.display_name} went flying! >:3',
            'certified kicks! 😤',
            'right in the shins! ouch 😬',
        ],
    },
    'punch': {
        'act': 'punches',
        'color': discord.Color.red(),
        'emoji': '👊',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'punch for you and you and you-!',
            'everyone is getting knocked out! 👊',
            'fists of fury! >:3',
            'nobody is dodging this one 😤',
        ],
        'desc_self': [
            'go rest and relax, no need to punch yourself :(',
            'please stop!! D:',
            'you okay there champ? 👊',
            'channel that energy elsewhere! :(',
        ],
        'desc_other': [
            'one punch coming right up!',
            'POW! 👊',
            '{user.display_name} didnt see that coming!',
            'straight to the face! >:D',
            'knocked em clean out! 💥',
        ],
    },
    'feed': {
        'act': 'feeds',
        'color': discord.Color.green(),
        'emoji': '🍰',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'how about some treats for everyone! :3',
            'snack time for all! 🍰',
            'feeding the whole squad 🥳',
            'nobody goes hungry today! 🍩',
        ],
        'desc_self': [
            'self-care is important, enjoy your treat! 🍩',
            'nom nom nom~ treating yourself! 🍰',
            'you deserve every bite! 🥰',
            'snacking solo, living the dream :3',
        ],
        'desc_other': [
            'gonna get you chonky! hehe :P',
            'open wide! 🍰',
            'feeding {user.display_name} like a baby bird :3',
            'nom nom nom! 🍩',
            'so well fed right now 😋',
        ],
    },
    'highfive': {
        'act': 'high-fives',
        'color': discord.Color.gold(),
        'emoji': '✋',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'team spirit! high five everyone! 🙌',
            'hands up for the whole squad! ✋',
            'group high five!! 🙌',
            'energy through the roof! ✨',
        ],
        'desc_self': [
            'clapping for yourself! you deserve it! 👏',
            'self high five! nice! ✋',
            'yes! nailed it! 🙌',
            'celebrating yourself is valid 🥳',
        ],
        'desc_other': [
            'nice one! *slap* 🙌',
            'SMACK! perfect high five ✋',
            '{user.display_name} left you hanging? rude :P',
            'teamwork makes the dream work! 🙌',
            'that one stung a little lol ✋',
        ],
    },
    'dance': {
        'act': 'is dancing',
        'color': discord.Color.purple(),
        'emoji': '💃',
        'lone': True,
        'link': 'with',
        'desc_everyone': [
            'dance party time! 🕺💃',
            'everybody on the floor! 💃',
            'the whole squad is moving! 🕺',
            'DJ drop the beat! 🎶',
        ],
        'desc_self': [
            'dancing like nobody is watching! :D',
            'solo dance break! 💃',
            'main character moment 🕺',
            'feeling the music~ 🎶',
        ],
        'desc_other': [
            'look at those moves! :3',
            'get it {user.display_name}! 💃',
            'duo dance activated 🕺',
            'the dancefloor belongs to them now 🎶',
            'somebody call a choreographer! 😲',
        ],
    },
    'sleep': {
        'act': 'is sleeping',
        'color': discord.Color.dark_grey(),
        'emoji': '😴',
        'lone': True,
        'link': 'with',
        'desc_everyone': [
            'everyone nap time! *zzz*',
            'lights out for the whole server 😴',
            'mass nap activated 💤',
            'shhh everyone is sleeping now 🤫',
        ],
        'desc_self': [
            'sweet dreams! 💤',
            'nap time well deserved 😴',
            'zzz... gone to dreamland 💭',
            'do not disturb! 🤫',
        ],
        'desc_other': [
            'shhh, let them rest! 🤫',
            'dont wake {user.display_name}!! 😴',
            'out cold 💤',
            'sleeping together how cute :3',
            'the pillow has been claimed 😴',
        ],
    },
    'cry': {
        'act': 'is crying',
        'color': discord.Color.blue(),
        'emoji': '😢',
        'lone': True,
        'link': 'with',
        'desc_everyone': [
            'group hug for the tears! 🫂',
            'everyone grab a tissue 😢',
            'collective sob session 💙',
            'its okay to cry together 🥺',
        ],
        'desc_self': [
            'aww {user.display_name} is lonely\n its okay to cry, let it out 💙',
            'its okay, let it all out 😢',
            '*passes tissues* 🥺',
            'crying it out is valid 💙',
            'we got you {user.display_name} 🫂',
        ],
        'desc_other': [
            'aww dont cry! *hugs* 🥺',
            'crying together 😢',
            'someone comfort them!! 🫂',
            '{user.display_name} better cheer {author.display_name} up! 💙',
            'the tears wont stop 😢',
        ],
    },
    'smile': {
        'act': 'is smiling',
        'color': discord.Color.gold(),
        'emoji': '😊',
        'lone': True,
        'link': 'at',
        'desc_everyone': [
            'smiles all around! :D',
            'happiness is contagious! 😊',
            'the whole server is glowing ✨',
            'best vibe check ever 😄',
        ],
        'desc_self': [
            'that smile looks good on you! 😄',
            'keep smiling! 😊',
            'self-happiness unlocked ✨',
            'radiant! absolutely radiant 😄',
        ],
        'desc_other': [
            'your smile is contagious! 😊',
            '{user.display_name} made that happen 😄',
            'look at that glow! ✨',
            'the sweetest smile 🥰',
            'now {user.display_name} is smiling too :3',
        ],
    },
    'think': {
        'act': 'is thinking',
        'color': discord.Color.teal(),
        'emoji': '🤔',
        'lone': True,
        'link': 'about',
        'desc_everyone': [
            'I wonder what the others are up to?',
            'big thoughts energy 🤔',
            'the whole squad is plotting something 👀',
            'collective brainpower activated 🧠',
        ],
        'desc_self': [
            'hmm what could it be? 🤔',
            'deep in thought...',
            'galaxy brain moment 🧠',
            'the gears are turning 🤔',
        ],
        'desc_other': [
            'they do that all day btw :3',
            'thinking about {user.display_name} huh~ 👀',
            'big thoughts about someone special 🤔',
            'what could it possibly mean 👀',
            'uh oh {user.display_name} is in trouble :P',
        ],
    },
    'wave': {
        'act': 'waves',
        'color': discord.Color.green(),
        'emoji': '👋',
        'lone': True,
        'link': 'at',
        'desc_everyone': [
            'hello everyone! 👋✨',
            'waving at the whole server! 👋',
            'hi hi hi hi hi! :D',
            'the friendliest hello 👋',
        ],
        'desc_self': [
            'hello me :D\n waving at the mirror? silly! :P',
            'hi me!! 👋',
            'waving at your reflection :P',
            'introducing yourself to yourself lol',
        ],
        'desc_other': [
            'wave back! dont be shy! :3',
            'hi {user.display_name}!! 👋',
            'dont leave them hanging! 😤',
            'the friendliest greeting~ 👋',
            '{user.display_name} better wave back :P',
        ],
    },
    'laugh': {
        'act': 'is laughing',
        'color': discord.Color.yellow(),
        'emoji': '😂',
        'lone': True,
        'link': 'with',
        'desc_everyone': [
            'everyone is laughing! what a mood! :P',
            'mass giggle attack 😂',
            'the whole server is losing it 🤣',
            'laughter is the best medicine! 😄',
        ],
        'desc_self': [
            'having a good time! keep it up! :D',
            'something is very funny apparently 😂',
            'losing it all by themselves lol',
            'the funniest person in the room :P',
        ],
        'desc_other': [
            'haha your laugh is adorable! :3',
            'laughing together!! 😂',
            'what did {user.display_name} say?? 🤣',
            'these two are a mess :P',
            'the laugh is contagious 😄',
        ],
    },
    'yeet': {
        'act': 'yeeted',
        'color': discord.Color.dark_purple(),
        'emoji': '🥏',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'bye bye everyone >:3',
            'everyone got yeeted! 🥏',
            'server cleared! >:D',
            'yeet yeet yeet! 💨',
        ],
        'desc_self': [
            'weeee',
            'self-yeet speedrun 🥏',
            'byeee~ 💨',
            'gone! just like that >:3',
        ],
        'desc_other': [
            'can {user.display_name} fly?',
            'YEET! 🥏',
            '{user.display_name} is now in orbit 💨',
            'gone! into the void >:3',
            'rip {user.display_name} 2024-2024 🥏',
        ],
    },
    'facepalm': {
        'act': 'facepalms',
        'color': discord.Color.dark_orange(),
        'emoji': '🤦',
        'lone': True,
        'link': 'at',
        'desc_everyone': [
            '*sigh* so uh why we facepalming?',
            'collective disappointment 🤦',
            'the whole server is done 😤',
            'everyone at the same time... wow',
        ],
        'desc_self': [
            "it's okay to be embarrassed *pat*",
            'we all have those moments 🤦',
            'took a big L huh :P',
            'its okay, nobody saw that... probably',
        ],
        'desc_other': [
            'you made {author.display_name} facepalm ._.',
            '{user.display_name} what did you do 🤦',
            'the disappointment is palpable 😤',
            '{author.display_name} expected better lol',
            'certified facepalm moment 🤦',
        ],
    },
    'baka': {
        'act': 'stoopid',
        'color': discord.Color.brand_green(),
        'emoji': '🦆',
        'lone': False,
        'link': ['said', 'is'],
        'desc_everyone': [
            '{author.display_name} included :P',
            'everyone qualifies apparently 🦆',
            'mass stoopid declaration >:3',
            'this server is a mess and {author.display_name} loves it :P',
        ],
        'desc_self': [
            "mybe you're but you are the special kind of stoopid :3",
            'certified self-awareness moment 🦆',
            'at least you know :P',
            'the stoopidest and the proudest :3',
        ],
        'desc_other': [
            '{author.display_name} said that not me ._.',
            'dont look at me 🦆',
            '{author.display_name} called it :P',
            'take it up with {author.display_name} lol',
            'the duck has spoken 🦆',
        ],
    },
    'nom': {
        'act': 'noms on',
        'color': discord.Color.orange(),
        'emoji': '😋',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'nom nom nom everyone! :P',
            'everyone is on the menu today 😋',
            'mass nomming in progress >:3',
            'so many noms so little time :P',
        ],
        'desc_self': [
            'nomming on yourself? silly goose! :3',
            'self-nom? bold choice 😋',
            'you taste good apparently :P',
            'weird flex but okay :3',
        ],
        'desc_other': [
            'tasty? hehe :3',
            'nom nom nom! 😋',
            '{user.display_name} has been nommed >:3',
            'delicious apparently :P',
            'chomp! sorry not sorry 😋',
        ],
    },
    'shoot': {
        'act': 'shoots',
        'color': discord.Color.red(),
        'emoji': '🔫',
        'lone': False,
        'link': '',
        'desc_everyone': [
            'pew pew everyone! 🔫',
            'nobody is safe! pew pew! 💥',
            'shooting gallery: server edition',
            'trigger happy today huh >:3',
        ],
        'desc_self': [
            'dont shoot yourself! D:',
            'please put that down!! 😟',
            'bad idea bad idea bad idea D:',
            'someone take that away from them!!',
        ],
        'desc_other': [
            'gotcha! *pew* 🎯',
            'BANG! 🔫',
            '{user.display_name} is down! 💥',
            'sniper mode activated 🎯',
            'clean shot! >:D',
        ],
    },
    'run': {
        'act': 'is running',
        'color': discord.Color.blue(),
        'emoji': '🏃',
        'lone': True,
        'link': 'with',
        'desc_everyone': [
            'everyone run! cardio time! 💨',
            'server-wide sprint! 🏃',
            'legs dont fail us now! 💨',
            'marathon activated! who finishes first? :P',
        ],
        'desc_self': [
            'running solo! nice workout! :D',
            'zoom zoom! 💨',
            'where are they going?? 🏃',
            'cardio arc has begun 💪',
        ],
        'desc_other': [
            'catch me if you can! 💨',
            'running together! 🏃',
            'keeping up with {user.display_name}? good luck :P',
            'speed duo! 💨',
            'race to the finish! 🏃',
        ],
    },
    'stare': {
        'act': 'stares',
        'color': discord.Color.dark_blue(),
        'emoji': '👁️',
        'lone': True,
        'link': 'at',
        'desc_everyone': [
            'staring contest! go! 👁️👁️',
            'eyes on everyone 👀',
            'the whole server feels watched 👁️',
            'no blinking allowed! 👁️👁️',
        ],
        'desc_self': [
            'staring at yourself? mirror time! :P',
            'the mirror stares back 👁️',
            'self-reflection moment :P',
            'who blinks first lol',
        ],
        'desc_other': [
            'dont blink! 👀',
            '{user.display_name} feels the eyes on them 👁️',
            'unblinking. unwavering. unsettling. :P',
            'the stare intensifies 👁️👁️',
            '{user.display_name} is very uncomfortable rn :P',
        ],
    },
    'thumbsup': {
        'act': 'gives thumbs up',
        'color': discord.Color.green(),
        'emoji': '👍',
        'lone': True,
        'link': 'to',
        'desc_everyone': [
            'thumbs up everyone! great job! 👍',
            'everyone gets the seal of approval! ✨',
            'certified good vibes only 👍',
            'wholesome server moment 🥰',
        ],
        'desc_self': [
            'nice work! you got this! 👍',
            'self-approval granted ✨',
            'believing in yourself! 👍',
            'you did that! own it! 😄',
        ],
        'desc_other': [
            'approval granted! ✨',
            '{user.display_name} earned that 👍',
            'seal of approval delivered! ✨',
            'big fan of {user.display_name} right now 👍',
            'yes! exactly! 👍',
        ],
    },
}

# ── Standalone reaction definitions ──────────────────────────────────────────
# Used by /look — no target, just the author expressing a feeling.
# Supports {author} format placeholder in title and description.
# description is a list — one entry is chosen randomly on each use
# Counter text: "{user} blushed X times"
REACTION = {
    'blush': {
        'title': '{author.display_name} is blushing',
        'description': [
            'awww how cute',
            'someone is flustered~ 🥰',
            'the redness cannot be hidden :P',
            'too cute for words 💕',
        ],
        'color': discord.Color.pink()
    },
    'shrug': {
        'title': '{author.display_name} shrugs',
        'description': [
            'shrugs like a rug',
            'not their problem :P',
            'the ultimate response 🤷',
            'couldnt care less lol',
        ],
        'color': discord.Color.dark_purple()
    },
    'yawn': {
        'title': '{author.display_name} yawned',
        'description': [
            'eepy {author.display_name} *pet*',
            'someone needs a nap 😴',
            'so tired... zzz 💤',
            'the yawn is contagious now thanks :P',
        ],
        'color': discord.Color.pink()
    },
    'angry': {
        'title': '{author.display_name} is angy >:(',
        'description': [
            'be careful everyone',
            'uh oh... >:(',
            'someone woke up and chose violence :P',
            'do not approach. do not make eye contact.',
        ],
        'color': discord.Color.red()
    },
    'bored': {
        'title': '{author.display_name} is bored to the bone',
        'description': [
            'bored? do a backflip :D!',
            'entertain them someone!! 😩',
            'the void is more interesting rn',
            'staring at the ceiling again huh :P',
        ],
        'color': discord.Color.gold()
    },
    'happy': {
        'title': '{author.display_name} is happy :3',
        'description': [
            'yayyy - happy for you too',
            'this energy is contagious! 😄',
            'good vibes only ✨',
            'the happiest person right now 🥳',
        ],
        'color': discord.Color.yellow()
    },
    'nope': {
        'title': '{author.display_name} noped out of here',
        'description': [
            'nope nah nuh uh never :P',
            'absolutely not. goodbye.',
            'left the chat mentally 💨',
            'not today satan :P',
        ],
        'color': discord.Color.brand_green()
    },
    'smug': {
        'title': '{author.display_name} looks smug',
        'description': [
            'someone is feeling confident :P',
            'they know something you dont 👀',
            'that smirk says everything :P',
            'certified smug moment ✨',
        ],
        'color': discord.Color.purple()
    },
    'lurk': {
        'title': '{author.display_name} is lurking',
        'description': [
            'watching from the shadows 👀',
            'they see everything 👁️',
            'silent but present :P',
            'lurk mode: activated 👀',
        ],
        'color': discord.Color.dark_grey()
    },
    'pout': {
        'title': '{author.display_name} is pouting',
        'description': [
            'aww that pout is too cute :3',
            'lower lip fully deployed 🥺',
            'someone give them what they want!! :P',
            'the poutest pout to ever pout 🥺',
        ],
        'color': discord.Color.purple()
    },
    'nod': {
        'title': '{author.display_name} nods',
        'description': [
            'nod of approval :)',
            'understood. agreed. noted. 👍',
            'silent agreement mode :)',
            'seal of acknowledgement granted ✨',
        ],
        'color': discord.Color.green()
    }
}

# Actions that use private counter format: "{author} kissed {user} X times"
PRIVATE_COUNTER_ACTIONS = {'kiss'}


# ── Counter text builder ──────────────────────────────────────────────────────
def build_counter_text(action: str, count: int, author_name: str, target_name: str | None, is_look: bool = False) -> str:
    """Build the -# counter line shown at the bottom of the embed description."""
    if count <= 0:
        return ''

    times = f'{count} time' if count == 1 else f'{count} times'

    if is_look:
        return f'-# {author_name} {action}ed {times}'

    if action in PRIVATE_COUNTER_ACTIONS and target_name:
        return f'-# {author_name} {action}ed {target_name} {times}'

    if target_name:
        return f'-# {target_name} got {action}ed {times}'

    return ''


# ── React back button view ────────────────────────────────────────────────────
class React_back(discord.ui.View):
    def __init__(self, author: discord.User, user: Optional[discord.User], action: str, show_button: bool = True):
        super().__init__()
        self.message: discord.WebhookMessage | None = None
        self.author = author
        self.action = action
        self.user = user
        self.action_data = ACTIONS[self.action]

        if show_button:
            self.react_back_button.label = button_text(self.action, self.action_data)
        else:
            self.remove_item(self.react_back_button)

    @discord.ui.button(label="React back!", style=discord.ButtonStyle.secondary, custom_id="react_back_button")
    async def react_back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.user and interaction.user != self.user:
            await interaction.response.send_message(f"Only {self.user.display_name} can react back!", ephemeral=True)
            return

        count = await increment_action_count(interaction.user.id, self.author.id, self.action)
        reward = await maybe_reward_dabloons(interaction.user.id)

        title = build_title(self.action, self.action_data, self.author.display_name, interaction.user.display_name, react_back=True)
        base_desc = random.choice(self.action_data['desc_other']).format(user=self.user, author=interaction.user)
        counter = build_counter_text(self.action, count, interaction.user.display_name, self.author.display_name)

        description = base_desc
        if counter:
            description += f'\n{counter}'
        if reward:
            description += f'\n-# ✨ +{reward} dabloons!'

        embed = await build_embed(self.action_data['color'], title, description, self.action, author=interaction.user)

        button.disabled = True
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)
        if self.message:
            await self.message.edit(view=self)


# ── Title builder ─────────────────────────────────────────────────────────────
def build_title(action: str, action_data: dict, author_name: str, target_name: str = None, everyone: bool = False, react_back: bool = False) -> str:
    emoji = action_data['emoji']
    act = action_data['act']
    link = action_data['link']

    if react_back:
        if action == 'baka':
            return f"**{emoji} {target_name} {link[0]} {author_name} {link[1]} {act} back! {emoji}**"
        elif action_data['lone']:
            return f"**{emoji} {target_name} {act} {link} {author_name} back! {emoji}**"
        else:
            return f"**{emoji} {target_name} {act} {author_name} back! {emoji}**"

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


# ── Button text ───────────────────────────────────────────────────────────────
def button_text(action: str, action_data: dict) -> str:
    if action_data["lone"]:
        return f"{ACTIONS[action]['emoji']} {action} with them"
    elif action == "nom":
        return f"{ACTIONS[action]['emoji']} {action} on them"
    elif action == "baka":
        return f"{ACTIONS[action]['emoji']} call {action} back"
    return f"{ACTIONS[action]['emoji']} {action} them back!"


# ── Embed builder ─────────────────────────────────────────────────────────────
async def build_embed(color: discord.Color, title: str, description: str, action: str, author: discord.User) -> discord.Embed:
    embed = discord.Embed(color=color, title=title, description=description)
    embed.set_image(url=await get_gif_url(action))
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.set_footer(text="quack quack quack")
    embed.timestamp = datetime.now()
    return embed


# ── GIF fetcher ───────────────────────────────────────────────────────────────
async def get_gif_url(action: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://nekos.best/api/v2/{action}") as response:
            data = await response.json()
            return data['results'][0]['url']


# ── Command setup ─────────────────────────────────────────────────────────────
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
            'hug', 'kiss', 'pat', 'poke', 'cuddle', 'bite', 'kick', 'punch',
            'feed', 'highfive', 'dance', 'sleep', 'cry', 'smile', 'think',
            'wave', 'laugh', 'yeet', 'facepalm', 'baka', 'nom', 'shoot',
            'run', 'stare', 'thumbsup'
        ],
        user: Optional[discord.User] = None,
        everyone: Optional[bool] = False
    ):
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            return

        try:
            await ensure_registered(interaction.user.id, str(interaction.user))

            action_data = ACTIONS[action]
            target_name = user.display_name if user else None
            title = build_title(action, action_data, interaction.user.display_name, target_name, everyone)

            # ── Description ───────────────────────────────────────────────────
            if everyone:
                base_desc = random.choice(action_data['desc_everyone']).format(user=interaction.user, author=interaction.user)
            elif user and user == interaction.user:
                base_desc = random.choice(action_data['desc_self']).format(user=interaction.user, author=interaction.user)
            elif user:
                base_desc = random.choice(action_data['desc_other']).format(user=user, author=interaction.user)
            else:
                base_desc = random.choice(action_data['desc_self']).format(user=interaction.user, author=interaction.user)

            # ── Counter (only when targeting another real user) ───────────────
            counter = ''
            if user and user != interaction.user and not everyone and not user.bot:
                count = await increment_action_count(interaction.user.id, user.id, action)
                counter = build_counter_text(action, count, interaction.user.display_name, user.display_name)

            # ── Dabloon reward ────────────────────────────────────────────────
            reward = await maybe_reward_dabloons(interaction.user.id)

            description = base_desc
            if counter:
                description += f'\n{counter}'
            if reward:
                description += f'\n-# ✨ +{reward} dabloons!'

            embed = await build_embed(action_data['color'], title, description, action, author=interaction.user)

            # ── Button — disabled for bot targets ─────────────────────────────
            show_button = not everyone and user != interaction.user and user is not None and not (user is not None and user.bot)
            view = React_back(interaction.user, user, action, show_button=show_button)

            if user is not None and user.bot:
                view.react_back_button.disabled = True

            view.message = await interaction.followup.send(embed=embed, view=view)

            # ── Easter egg: targeting Amber herself ───────────────────────────
            if user == bot.user:
                bot_title = build_title(action, action_data, bot.user.display_name, interaction.user.display_name)
                bot_desc = random.choice(action_data['desc_other']).format(user=interaction.user, author=bot.user)
                bot_embed = await build_embed(action_data['color'], bot_title, bot_desc, action, author=bot.user)
                await interaction.followup.send(embed=bot_embed)

            # ── 50% chance to react back when targeting another bot ────────────
            elif user is not None and user.bot and user != bot.user and random.random() < 0.5:
                bot_title = build_title(action, action_data, user.display_name, interaction.user.display_name)
                bot_desc = random.choice(action_data['desc_other']).format(user=interaction.user, author=user)
                bot_embed = await build_embed(action_data['color'], bot_title, bot_desc, action, author=user)
                await interaction.followup.send(embed=bot_embed)

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="look", description="Give a reaction with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(reaction="Choose a reaction to perform")
    async def do_reaction(
        interaction: discord.Interaction,
        reaction: Literal[
            'blush', 'shrug', 'yawn', 'angry', 'bored', 'happy',
            'nope', 'smug', 'lurk', 'pout', 'nod'
        ]
    ):
        await interaction.response.defer()
        try:
            await ensure_registered(interaction.user.id, str(interaction.user))

            reaction_data = REACTION[reaction]
            title = reaction_data['title'].format(author=interaction.user)
            base_desc = random.choice(reaction_data['description']).format(author=interaction.user)

            # Counter: "{user} blushed X times"
            count = await increment_action_count(interaction.user.id, None, reaction)
            counter = build_counter_text(reaction, count, interaction.user.display_name, None, is_look=True)

            # Dabloon reward
            reward = await maybe_reward_dabloons(interaction.user.id)

            description = base_desc
            if counter:
                description += f'\n{counter}'
            if reward:
                description += f'\n-# ✨ +{reward} dabloons!'

            embed = await build_embed(reaction_data['color'], title, description, reaction, author=interaction.user)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="**Error**",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
