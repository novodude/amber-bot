import random
from collections import deque
import discord
from discord import app_commands
from discord.ext import commands

# Chance (0.0 - 1.0) of sending a random past message instead of the current one
HISTORY_CHANCE = 0.30
HISTORY_SIZE = 15

# Stored message snapshot: just what we need to re-send
class _Snap:
    __slots__ = ("content", "attachment_urls", "sticker_names")
    def __init__(self, message: discord.Message):
        self.content: str = message.content or ""
        self.attachment_urls: list[str] = [a.url for a in message.attachments]
        self.sticker_names: list[str] = [s.name for s in message.stickers]


class Mimic(commands.Cog):
    """Mirrors every message sent by a target user in the same guild."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Maps guild_id -> set of user_ids being mimicked
        self._targets: dict[int, set[int]] = {}
        # Maps (guild_id, user_id) -> deque of _Snap
        self._history: dict[tuple[int, int], deque[_Snap]] = {}

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #

    def _is_mimicked(self, guild_id: int, user_id: int) -> bool:
        return user_id in self._targets.get(guild_id, set())

    def _add_target(self, guild_id: int, user_id: int) -> None:
        self._targets.setdefault(guild_id, set()).add(user_id)
        self._history.setdefault((guild_id, user_id), deque(maxlen=HISTORY_SIZE))

    def _remove_target(self, guild_id: int, user_id: int) -> bool:
        """Returns True if the target was present and removed."""
        targets = self._targets.get(guild_id, set())
        if user_id in targets:
            targets.discard(user_id)
            self._history.pop((guild_id, user_id), None)
            return True
        return False

    def _push_history(self, guild_id: int, user_id: int, message: discord.Message) -> None:
        key = (guild_id, user_id)
        if key not in self._history:
            self._history[key] = deque(maxlen=HISTORY_SIZE)
        self._history[key].append(_Snap(message))

    def _random_past(self, guild_id: int, user_id: int) -> "_Snap | None":
        history = self._history.get((guild_id, user_id))
        if not history:
            return None
        return random.choice(list(history))

    # ------------------------------------------------------------------ #
    #  Admin check                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _invoker_is_admin(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        return member.guild_permissions.administrator
        return True

    # ------------------------------------------------------------------ #
    #  /mimic start                                                      #
    # ------------------------------------------------------------------ #

    mimic_group = app_commands.Group(
        name="mimic",
        description="Make the bot repeat a user's messages.",
        guild_only=True,
    )

    @mimic_group.command(name="start", description="Start mimicking a user.")
    @app_commands.describe(target="The member whose messages will be mirrored.")
    async def mimic_start(
        self, interaction: discord.Interaction, target: discord.Member
    ) -> None:
        if not self._invoker_is_admin(interaction):
            await interaction.response.send_message(
                "⛔ Only admins can use this command.", ephemeral=True
            )
            return

        if target.bot:
            await interaction.response.send_message(
                "❌ You can't mimic a bot.", ephemeral=True
            )
            return

        if target.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You can't mimic yourself.", ephemeral=True
            )
            return

        guild_id = interaction.guild_id  # type: ignore[union-attr]

        if self._is_mimicked(guild_id, target.id):
            await interaction.response.send_message(
                f"ℹ️ Already mimicking **{target.display_name}**.", ephemeral=True
            )
            return

        self._add_target(guild_id, target.id)
        await interaction.response.send_message(
            f"🦜 Now mimicking **{target.display_name}**. "
            f"Use `/mimic stop` to stop.",
            ephemeral=True,
        )

    # ------------------------------------------------------------------ #
    #  /mimic stop                                                       #
    # ------------------------------------------------------------------ #

    @mimic_group.command(name="stop", description="Stop mimicking a user.")
    @app_commands.describe(target="The member to stop mimicking.")
    async def mimic_stop(
        self, interaction: discord.Interaction, target: discord.Member
    ) -> None:
        if not self._invoker_is_admin(interaction):
            await interaction.response.send_message(
                "⛔ Only admins can use this command.", ephemeral=True
            )
            return

        guild_id = interaction.guild_id  # type: ignore[union-attr]

        if self._remove_target(guild_id, target.id):
            await interaction.response.send_message(
                f"🛑 Stopped mimicking **{target.display_name}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ **{target.display_name}** wasn't being mimicked.", ephemeral=True
            )

    # ------------------------------------------------------------------ #
    #  /mimic list                                                       #
    # ------------------------------------------------------------------ #

    @mimic_group.command(name="list", description="List all currently mimicked users.")
    async def mimic_list(self, interaction: discord.Interaction) -> None:
        if not self._invoker_is_admin(interaction):
            await interaction.response.send_message(
                "⛔ Only admins can use this command.", ephemeral=True
            )
            return

        guild_id = interaction.guild_id  # type: ignore[union-attr]
        targets = self._targets.get(guild_id, set())

        if not targets:
            await interaction.response.send_message(
                "ℹ️ No users are being mimicked right now.", ephemeral=True
            )
            return

        lines = []
        for uid in targets:
            member = interaction.guild.get_member(uid)  # type: ignore[union-attr]
            lines.append(f"• {member.mention if member else f'<@{uid}>'}")

        await interaction.response.send_message(
            "**Currently mimicking:**\n" + "\n".join(lines), ephemeral=True
        )

    # ------------------------------------------------------------------ #
    #  handle_mimic —                                                    #
    # ------------------------------------------------------------------ #

    async def handle_mimic(self, message: discord.Message) -> None:
        if (
            not message.guild
            or message.author.bot
            or message.type != discord.MessageType.default
            or not self._is_mimicked(message.guild.id, message.author.id)
        ):
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Always store the incoming message before deciding what to send
        self._push_history(guild_id, user_id, message)

        # Roll — use a past message or mirror the current one
        past = self._random_past(guild_id, user_id) if random.random() < HISTORY_CHANCE else None

        if past:
            # Re-send a stored snapshot (attachments become plain URLs since they can't be re-fetched)
            content = past.content
            if past.sticker_names:
                content += "\n*(sticker: " + ", ".join(past.sticker_names) + ")*"
            if past.attachment_urls:
                content += "\n" + "\n".join(past.attachment_urls)
            if content.strip():
                await message.channel.send(content)
        else:
            # Mirror the current message with live attachment re-fetch
            content = message.content or ""

            files: list[discord.File] = []
            for attachment in message.attachments:
                try:
                    files.append(await attachment.to_file(use_cached=True))
                except discord.HTTPException:
                    pass

            if message.stickers:
                content += "\n*(sticker: " + ", ".join(s.name for s in message.stickers) + ")*"

            if content.strip() or files:
                await message.channel.send(
                    content=content if content.strip() else None,
                    files=files or [],
                )


# ------------------------------------------------------------------ #
#  Setup                                                             #
# ------------------------------------------------------------------ #

async def mimic_setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mimic(bot))
