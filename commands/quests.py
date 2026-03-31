import discord
from discord import app_commands
from discord.ext import commands
from utils.userbase.ensure_registered import ensure_registered
from utils.quests import get_user_daily_quests, claim_quest


def build_progress_bar(progress: int, target: int, length: int = 10) -> str:
    """Build a simple text progress bar."""
    filled = int((progress / target) * length) if target > 0 else 0
    filled = min(filled, length)
    empty = length - filled
    return f"{'█' * filled}{'░' * empty} {progress}/{target}"


def build_quests_embed(user: discord.User, quests: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="📋 Daily Quests",
        description="Complete quests to earn dabloons and XP!\nRefreshes every day.",
        color=discord.Color.gold()
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    for quest in quests:
        target = quest["effective_target"]
        progress = quest["progress"]
        completed = quest["completed"]
        claimed = quest["claimed"]

        # build description with word placeholder filled in
        desc = quest["description"].format(
            target=target,
            target_value=quest.get("target_value") or "???"
        )

        if claimed:
            status = "✅ Claimed"
        elif completed:
            status = "🎁 Ready to claim — use `/quests claim`"
        else:
            status = build_progress_bar(progress, target)

        rewards = f"🪙 {quest['reward_dabloons']} dabloons • ✨ {quest['reward_xp']} XP"

        embed.add_field(
            name=f"{'~~' if claimed else ''}{quest['title']}{'~~' if claimed else ''}",
            value=f"{desc}\n{status}\n-# {rewards}",
            inline=False
        )

    embed.set_footer(text="quacking good!")
    return embed


class QuestsView(discord.ui.View):
    def __init__(self, discord_id: int, quests: list[dict]):
        super().__init__(timeout=120)
        self.discord_id = discord_id
        self.quests = quests
        self._add_claim_buttons()

    def _add_claim_buttons(self):
        # add a claim button for each completed but unclaimed quest
        for quest in self.quests:
            if quest["completed"] and not quest["claimed"]:
                button = discord.ui.Button(
                    label=f"Claim: {quest['title']}",
                    style=discord.ButtonStyle.success,
                    custom_id=f"claim_{quest['daily_quest_id']}",
                    emoji="🎁"
                )
                button.callback = self._make_claim_callback(quest["daily_quest_id"])
                self.add_item(button)

    def _make_claim_callback(self, daily_quest_id: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.discord_id:
                await interaction.response.send_message("These aren't your quests!", ephemeral=True)
                return

            success, message, dabloons, xp = await claim_quest(interaction.user.id, daily_quest_id)

            if not success:
                await interaction.response.send_message(message, ephemeral=True)
                return

            # refresh quests and rebuild embed
            updated_quests = await get_user_daily_quests(interaction.user.id)
            new_view = QuestsView(self.discord_id, updated_quests)
            embed = build_quests_embed(interaction.user, updated_quests)

            reward_embed = discord.Embed(
                title="🎉 Quest Reward Claimed!",
                description=f"🪙 **+{dabloons} dabloons**\n✨ **+{xp} XP**",
                color=discord.Color.green()
            )

            await interaction.response.edit_message(embed=embed, view=new_view)
            await interaction.followup.send(embed=reward_embed, ephemeral=True)

        return callback


class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quests", description="View your daily quests")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def quests(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await ensure_registered(interaction.user.id, str(interaction.user))
        quests = await get_user_daily_quests(interaction.user.id)

        if not quests:
            await interaction.followup.send("Something went wrong fetching your quests. Try registering first with `/register`.", ephemeral=True)
            return

        embed = build_quests_embed(interaction.user, quests)
        view = QuestsView(interaction.user.id, quests)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
