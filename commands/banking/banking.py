import discord
import aiosqlite
from discord import ui
from datetime import datetime
from discord import app_commands


class ColorSelect(ui.Select):
    def __init__(self, profile_view: 'ProfileView'):
        self.profile_view = profile_view
        options = [
            discord.SelectOption(label="Gold", emoji="🟡", value="gold", description="Classic gold color"),
            discord.SelectOption(label="Blue", emoji="🔵", value="blue", description="Cool blue"),
            discord.SelectOption(label="Red", emoji="🔴", value="red", description="Bold red"),
            discord.SelectOption(label="Green", emoji="🟢", value="green", description="Fresh green"),
            discord.SelectOption(label="Purple", emoji="🟣", value="purple", description="Royal purple"),
            discord.SelectOption(label="Orange", emoji="🟠", value="orange", description="Vibrant orange"),
            discord.SelectOption(label="Pink", emoji="💖", value="pink", description="Lovely pink"),
            discord.SelectOption(label="Dark Blue", emoji="🌊", value="dark_blue", description="Deep ocean blue"),
        ]
        super().__init__(
            placeholder="Select your profile color",
            min_values=1,
            max_values=1,
            options=options
        )
    async def callback(self, interaction: discord.Interaction):
        color_value = self.values[0]
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            await db.execute("UPDATE users SET profile_color = ? WHERE discord_id = ?", (color_value, user_id))
            await db.commit()
        embed = discord.Embed(
            title="Profile Color Updated",
            description=f"Your profile color has been updated to **{color_value.replace('_', ' ')}**.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.profile_view.refresh_profile(interaction)


class SetBioModal(ui.Modal, title="Set Your Bio"):
    bio_input = ui.TextInput(
        label="Enter your new bio",
        style=discord.TextStyle.paragraph,
        placeholder="Type your bio here...",
        max_length=200,
    )
    
    def __init__(self, profile_view: 'ProfileView'):
        super().__init__()
        self.profile_view = profile_view
    
    async def on_submit(self, interaction: discord.Interaction):
        new_bio = self.bio_input.value
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            await db.execute("UPDATE users SET bio = ? WHERE discord_id = ?", (new_bio, user_id))
            await db.commit()
        
        embed = discord.Embed(
            title="Bio Updated",
            description=f"Your bio has been updated to:\n\n{new_bio}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if self.profile_view:
            await self.profile_view.refresh_profile(interaction)


class BioEditView(ui.View):
    def __init__(self, user_id: int, profile_view: 'ProfileView'):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.profile_view = profile_view

    @discord.ui.button(label="edit bio", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_bio_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetBioModal(self.profile_view)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="clear bio", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_bio_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            await db.execute("UPDATE users SET bio = ? WHERE discord_id = ?", ("This user has no bio set.", user_id))
            await db.commit()
        
        embed = discord.Embed(
            title="Bio Cleared",
            description="Your bio has been cleared.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if self.profile_view:
            await self.profile_view.refresh_profile(interaction)
    
    @discord.ui.button(label="back to profile", style=discord.ButtonStyle.secondary, emoji="🔙")
    async def back_to_profile(self, interaction: discord.Interaction, button: ui.Button):
        await self.profile_view.refresh_profile(interaction)



class ProfileView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    def get_color(self, color_name: str):
        """Convert color name to discord.Color"""
        colors = {
            "gold": discord.Color.gold(),
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "purple": discord.Color.purple(),
            "orange": discord.Color.orange(),
            "pink": discord.Color.from_rgb(255, 192, 203),
            "dark_blue": discord.Color.dark_blue(),
        }
        return colors.get(color_name, discord.Color.gold())
    
    async def refresh_profile_message(self, interaction: discord.Interaction):
        """Refresh the profile by editing the original message"""
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT amber_dabloons, bio, profile_color FROM users WHERE discord_id = ?", (self.user_id,))
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            bio = row[1] if row and row[1] else "This user has no bio set."
            color_name = row[2] if row and row[2] else "gold"
        
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            greeting_time = "morning"
        elif 12 <= current_hour < 17:
            greeting_time = "afternoon"
        elif 17 <= current_hour < 21:
            greeting_time = "evening"
        else:
            greeting_time = "night"
        
        embed = discord.Embed(
            title=f"good {greeting_time}, {interaction.user.name}!",
            description=f"{bio}",
            color=self.get_color(color_name)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)
        embed.set_footer(text="quacking good!")
        
        # Edit the original message
        await interaction.message.edit(embed=embed, view=self)
    
    async def refresh_profile(self, interaction: discord.Interaction):
        """Helper method to refresh the profile embed"""
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT amber_dabloons, bio, profile_color FROM users WHERE discord_id = ?", (self.user_id,))
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            bio = row[1] if row and row[1] else "This user has no bio set."
            color_name = row[2] if row and row[2] else "gold"
        
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            greeting_time = "morning"
        elif 12 <= current_hour < 17:
            greeting_time = "afternoon"
        elif 17 <= current_hour < 21:
            greeting_time = "evening"
        else:
            greeting_time = "night"
        
        embed = discord.Embed(
            title=f"good {greeting_time}, {interaction.user.name}!",
            description=f"{bio}",
            color=self.get_color(color_name)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)
        embed.set_footer(text="quacking good!")
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="Refresh Balance", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh_balance(self, interaction: discord.Interaction, button: ui.Button):
        await self.refresh_profile(interaction)
    
    @discord.ui.button(label="Edit Bio", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_bio(self, interaction: discord.Interaction, button: ui.Button):
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT bio FROM users WHERE discord_id = ?", (self.user_id,))
            row = await cursor.fetchone()
            current_bio = row[0] if row and row[0] else "This user has no bio set."
        
        embed = discord.Embed(
            title="✏️ Edit Your Bio",
            description=f"**Current Bio:**\n{current_bio}\n\nUse the buttons below to edit or clear your bio.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click 'Edit Bio' to open the editor")
        
        view = BioEditView(self.user_id, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Customize", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def customize_profile(self, interaction: discord.Interaction, button: ui.Button):
        # Fetch current color
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT profile_color FROM users WHERE discord_id = ?", (self.user_id,))
            row = await cursor.fetchone()
            current_color = row[0] if row and row[0] else "gold"
        
        embed = discord.Embed(
            title="🎨 Customize Your Profile",
            description=f"**Current Color:** {current_color}\n\nSelect a color from the dropdown below to change your profile theme!",
            color=self.get_color(current_color)
        )
        
        customize_view = ui.View(timeout=60)
        customize_view.add_item(ColorSelect(self))
        
        back_button = ui.Button(label="Back to Profile", style=discord.ButtonStyle.secondary, emoji="🔙")
        async def back_callback(button_interaction: discord.Interaction):
            await self.refresh_profile(button_interaction)
        back_button.callback = back_callback
        customize_view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=customize_view)
    
    @discord.ui.button(label="Wallet", style=discord.ButtonStyle.success, emoji="💰")
    async def view_wallet(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Opening wallet... (This feature is under development.)",
            ephemeral=True
        )



async def banking_setup(bot):
    @bot.tree.command(name="profile", description="Check your profile.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def profile(interaction: discord.Interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT discord_id FROM users WHERE discord_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                embed = discord.Embed(
                    title="Profile Not Found",
                    description=f"{interaction.user.mention} is not registered in the banking system. Please do `/register` to use the profile features.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            cursor = await db.execute("SELECT amber_dabloons, bio FROM users WHERE discord_id = ?", (user_id,))
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            bio = row[1] if row and row[1] else "This user has no bio set."
        
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            greeting_time = "morning"
        elif 12 <= current_hour < 17:
            greeting_time = "afternoon"
        elif 17 <= current_hour < 21:
            greeting_time = "evening"
        else:
            greeting_time = "night"
        
        embed = discord.Embed(
            title=f"good {greeting_time}, {interaction.user.name}!",
            description=f"{bio}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)
        embed.set_footer(text="quacking good!")
        
        view = ProfileView(user_id)
        await interaction.response.send_message(embed=embed, view=view)
    @bot.tree.command(name="setbio", description="Set your custom bio")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def setbio(interaction: discord.Interaction, bio: str):
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT discord_id FROM users WHERE discord_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                embed = discord.Embed(
                    title="Not Registered",
                    description=f"{interaction.user.mention} is not registered. Please do `/register` first.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await db.execute("UPDATE users SET bio = ? WHERE discord_id = ?", (bio, user_id))
            await db.commit()
        
        embed = discord.Embed(
            title="Bio Updated",
            description=f"Your bio has been set to:\n\n{bio}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @bot.tree.command(name="register", description="Register in the system.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def register(interaction: discord.Interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute("SELECT discord_id FROM users WHERE discord_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                embed = discord.Embed(
                    title="Already Registered",
                    description=f"{interaction.user.mention} is already registered in the banking system.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await db.execute("INSERT INTO users (discord_id, amber_dabloons, username) VALUES (?, ?, ?)", (user_id, 50, str(interaction.user)))
            await db.commit()
                
        embed = discord.Embed(
            title="Registration Successful",
            description=f"{interaction.user.mention} has been registered in the banking system with a starting balance of 50 dabloons!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
