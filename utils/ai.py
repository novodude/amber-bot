import g4f
import discord
from discord.ext import commands
from g4f.client import AsyncClient
from collections import defaultdict, deque
from utils.text import pretty_text

client = AsyncClient()

async def ask_ai(history: list[dict], system_prompt: str,) -> str:
    """
    history: list of {"role": "user"/"assistant", "content": "username: message"}
    returns amber's reply as plain text, or empty string if she should stay silent
    """
    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response = await client.chat.completions.create(
            model=g4f.models.default,
            messages=messages,
            timeout=30,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"g4f error: {e}")
        return ""




async def format_message_for_history(message: discord.Message, bot: commands.Bot | None = None) -> str:
    """Turn a discord.Message into a single history line: 'username: content'"""
    parts = []

    if message.content:
        parts.append(await pretty_text(text=message.content, bot=bot, interaction=None))

    if message.attachments:
        names = ", ".join(a.filename for a in message.attachments)
        parts.append(f"[attached: {names}]")

    if message.embeds:
        for embed in message.embeds:
            title = embed.title or ""
            desc = embed.description or ""
            embed_text = " - ".join(p for p in (title, desc) if p)
            if embed_text:
                parts.append(f"[embed: {embed_text}]")

    if message.stickers:
        parts.append(f"[sticker: {message.stickers[0].name}]")

    content = " ".join(parts) if parts else "[empty message]"
    return f"{message.author.display_name}: {content}"


MAX_HISTORY = 20  # tune this — how many messages amber "remembers" per channel

amber_history: dict[int, deque[dict]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

def add_to_history(channel_id: int, role: str, content: str) -> None:
    amber_history[channel_id].append({"role": role, "content": content})

def get_history(channel_id: int) -> list[dict]:
    return list(amber_history[channel_id])
