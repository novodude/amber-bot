import discord
import discord.ui as ui
from discord import app_commands

class DuckClicker(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.click_count = 0
        
    @discord.ui.button(label="increase", style=discord.ButtonStyle.primary)
    async def click_button(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user:
            return
        self.click_count += 1
        await interaction.response.edit_message(
            content=f"{self.click_count} ducks quacked! 🦆",
            view=self
        )



async def minigames_setup(bot):

    @bot.tree.command(name="duck_clicker", description="Click the buttons to quack ducks!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def test_command(interaction: discord.Interaction):
        view = DuckClicker()
        await interaction.response.send_message("0 ducks quacked! 🦆", view=view)

