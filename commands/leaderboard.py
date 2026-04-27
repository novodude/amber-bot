import discord
from utils.economy import get_leaderboard, set_private_account, is_private_account


EMOJI_MAP = {
    "money": "🪙",
    "level": "⭐",
    "actions received": "🤝",
    "action given": "🙌",
    "duck clicker": "🦆",
    "ttt": "⚔️",
    "ttt streak": "🔥"
}

class LeaderboardType(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Money", value="money", emoji="🪙"),
            discord.SelectOption(label="Level", value="level", emoji="⭐"),
            discord.SelectOption(label="Actions Received", value="actions received", emoji="🤝"),
            discord.SelectOption(label="Actions Given", value="action given", emoji="🙌"),
            discord.SelectOption(label="Duck Clicker", value="duck clicker", emoji="🦆"),
            discord.SelectOption(label="TTT Wins", value="ttt", emoji="⚔️"),
            discord.SelectOption(label="TTT Streak", value="ttt streak", emoji="🔥")
        ]
        super().__init__(placeholder="Select leaderboard type...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_type = self.values[0]
        leaderboard = await get_leaderboard(selected_type)


        if not leaderboard:
            await interaction.response.send_message("No users found in the leaderboard.")
            return

        embed = discord.Embed(
            title=f"{selected_type.capitalize()} Leaderboard",
            description=f"Top 10 users by {selected_type}",
            color=discord.Color.gold()
        )

        for rank, (username, value) in enumerate(leaderboard, start=1):
            embed.add_field(
                name=f"{rank}. {username}",
                value=f"{EMOJI_MAP.get(selected_type, '')} {value}",
                inline=False
            )

        await interaction.response.edit_message(embed=embed)

class LeaderboardUI(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LeaderboardType())


async def leaderboard_setup(bot):
    @bot.tree.command(name="switchprivacy", description="Toggle your account's privacy setting for leaderboards.")
    async def switchprivacy(interaction: discord.Interaction):
        discord_id = interaction.user.id
        current_privacy = await is_private_account(discord_id)
        new_privacy = not current_privacy
        await set_private_account(discord_id, new_privacy)

        status = "private" if new_privacy else "public"
        await interaction.response.send_message(f"Your account is now {status} for leaderboards.", ephemeral=True)

    @bot.tree.command(name="leaderboard", description="View the dabloon leaderboard!")
    async def leaderboard(interaction: discord.Interaction):
        leaderboard = await get_leaderboard("level")

        if not leaderboard:
            await interaction.response.send_message("No users found in the leaderboard.")
            return

        embed = discord.Embed(
            title="Dabloon Leaderboard",
            description="Top 10 users by dabloon balance",
            color=discord.Color.gold()
        )

        for rank, (username, value) in enumerate(leaderboard, start=1):
            embed.add_field(name=f"{rank}. {username}", value=f"{EMOJI_MAP['level']} {value}", inline=False)

        await interaction.response.send_message(embed=embed, view=LeaderboardUI())
