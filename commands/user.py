from typing import Literal
import discord
from discord import app_commands
from utils.reactions import ACTIONS
from utils.action_counts import get_all_action_data

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class User(app_commands.Group):
    """User related commands"""

    @app_commands.command(name="info", description="Get information about a user")
    @app_commands.describe(user="The user to get information about")
    async def info(self, interaction: discord.Interaction, user: discord.User):
        """Get information about a user"""
        embed = discord.Embed(title=f"{user.name}'s Information", color=discord.Color.blue())
        embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(name="Username", value=user.name, inline=True)
        embed.add_field(name="created_at", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="avatar", description="get the user avatar")
    @app_commands.describe(user="The user to get their avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.User):
        embed = discord.Embed(title=f"{user.name}'s avatar", color=discord.Color.brand_green())
        embed.set_image(url=user.avatar.url)
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="banner", description="get the user banner")
    @app_commands.describe(user="The user to get their avatar")
    async def banner(self, interaction: discord.Interaction, user: discord.User):
        if user.banner is None:
            await interaction.response.send_message("This user does not have a banner.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{user.name}'s banner", color=discord.Color.brand_green())
        embed.set_image(url=user.banner.url)
        await interaction.response.send_message(embed=embed)



class StatsType(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Actions Received",
                value="Actions Received",
                emoji="🤝"
            ),
            discord.SelectOption(
                label="Actions Given",
                value="Actions Given",
                emoji="🙌"
            )
        ]

        super().__init__(
            placeholder="Select action type...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_type = self.values[0]

        data = await get_all_action_data(interaction.user.id, selected_type)

        if not data:
            await interaction.response.send_message(
                "No data found for you.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=selected_type,
            description=f"{interaction.user.display_name}'s {selected_type}",
            color=discord.Color.gold()
        )

        for action, value in data:
            embed.add_field(
                name=f"{action} | {ACTIONS[action]['emoji']}",
                value=f"{value} times",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self.view)

class StatsUI(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StatsType())

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class My(app_commands.Group):
    """commands for managing and viewing data stored inside amber db"""
    @app_commands.command(name="stats", description="show your action stats")
    @app_commands.describe(type="hugs you gave or received")
    async def stats(self, interaction: discord.Interaction, type: Literal["Actions Given", "Actions Received"]):
        
        data = await get_all_action_data(interaction.user.id, type)

        if not data:
            await interaction.response.send_message("No data found for you.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{type.capitalize()}",
            description=f"{interaction.user.display_name}'s {type}",
            color=discord.Color.gold()
        )

        for action, value in data:
            embed.add_field(
                name=f"{action} | {ACTIONS[action]['emoji']}",
                value=f"{value} times",
                inline=False
            )
        view = StatsUI()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def user_setup(bot):
    bot.tree.add_command(User())
    bot.tree.add_command(My())
