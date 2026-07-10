import discord
import re
from discord.ext import commands

CUSTOM_EMOJI_RE = re.compile(r'<a?:(\w+):\d+>')
UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B50-\U00002B55"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+", flags=re.UNICODE
)
MENTION_RE = re.compile(r'<@!?(\d+)>')
ROLE_MENTION_RE = re.compile(r'<@&(\d+)>')
CHANNEL_RE = re.compile(r'<#(\d+)>')


def normalize_custom_emojis(text):
    return CUSTOM_EMOJI_RE.sub(lambda m: f'[{m.group(1)}]', text)

def mention_to_name(text: str, bot: commands.Bot | None = None, interaction: discord.Interaction | None = None) -> str:
    """Replace <@id>, <#id>, <@&id> mentions in text with @name / #name."""
    guild = interaction.guild if interaction else None

    def user_name(user_id: int) -> str | None:
        if guild:
            member = guild.get_member(user_id)
            if member:
                return member.display_name
        if bot:
            user = bot.get_user(user_id)
            return user.name if user else None
        return None

    def channel_name(channel_id: int) -> str | None:
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                return channel.name
        if bot:
            channel = bot.get_channel(channel_id)
            return channel.name if channel else None
        return None

    def role_name(role_id: int) -> str | None:
        if guild:
            role = guild.get_role(role_id)
            if role:
                return role.name
        if bot:
            for g in bot.guilds:
                role = g.get_role(role_id)
                if role:
                    return role.name
        return None

    text = MENTION_RE.sub(lambda m: f'@{user_name(int(m.group(1))) or m.group(0)}', text)
    text = CHANNEL_RE.sub(lambda m: f'#{channel_name(int(m.group(1))) or m.group(0)}', text)
    text = ROLE_MENTION_RE.sub(lambda m: f'@{role_name(int(m.group(1))) or m.group(0)}', text)
    return text

async def pretty_text(interaction: discord.Interaction, bot: commands.Bot, text: str) -> str:
    """
    use it to clean text from mention 
    to images or other stuff that need the mention to be name!
    """
    text = normalize_custom_emojis(text)
    text = mention_to_name(interaction=interaction, bot=bot, text=text)
    return text


