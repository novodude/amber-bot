import discord
import aiosqlite
from discord import ui
from utils.economy import get_dabloons, get_user_id_from_discord
from utils.action_counts import get_total_actions_performed, get_received_count

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
        if self.user_id != interaction.user.id:
            return
        modal = SetBioModal(self.profile_view)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="clear bio", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_bio_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return
        async with aiosqlite.connect("data/user.db") as db:
            await db.execute(
                "UPDATE users SET bio = ? WHERE discord_id = ?",
                ("This user has no bio set.", interaction.user.id)
            )
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
        if self.user_id != interaction.user.id:
            return
        await self.profile_view.refresh_profile(interaction)


class ProfileView(ui.View):
    def __init__(self, discord_id: int):
        super().__init__(timeout=None)
        self.discord_id = discord_id

    def get_color(self, color_name: str):
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
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT bio, profile_color FROM users WHERE discord_id = ?", (self.discord_id,)
            )
            row = await cursor.fetchone()
            bio = row[0] if row and row[0] else "This user has no bio set."
            color_name = row[1] if row and row[1] else "gold"

        balance = await get_dabloons(await get_user_id_from_discord(self.discord_id))

        current_hour = discord.utils.utcnow().hour
        greeting_time = (
            "morning" if 5 <= current_hour < 12 else
            "afternoon" if 12 <= current_hour < 17 else
            "evening" if 17 <= current_hour < 21 else
            "night"
        )

        embed = discord.Embed(
            title=f"good {greeting_time}, {interaction.user.name}!",
            description=bio,
            color=self.get_color(color_name)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)
        embed.set_footer(text="quacking good!")

        await interaction.message.edit(embed=embed, view=self)

    async def refresh_profile(self, interaction: discord.Interaction):
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT bio, profile_color FROM users WHERE discord_id = ?", (self.discord_id,)
            )
            row = await cursor.fetchone()
            bio = row[0] if row and row[0] else "This user has no bio set."
            color_name = row[1] if row and row[1] else "gold"

        balance = await get_dabloons(await get_user_id_from_discord(self.discord_id))

        current_hour = discord.utils.utcnow().hour
        greeting_time = (
            "morning" if 5 <= current_hour < 12 else
            "afternoon" if 12 <= current_hour < 17 else
            "evening" if 17 <= current_hour < 21 else
            "night"
        )

        embed = await build_profile_embed(
            discord_id=self.discord_id,
            user=interaction.user,
            balance=balance,
            bio=bio,
            color=self.get_color(color_name),
            greeting_time=greeting_time,
        )

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Refresh profile", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh_balance(self, interaction: discord.Interaction, button: ui.Button):
        if self.discord_id != interaction.user.id:
            return
        await self.refresh_profile(interaction)

    @discord.ui.button(label="Edit Bio", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_bio(self, interaction: discord.Interaction, button: ui.Button):
        if self.discord_id != interaction.user.id:
            return
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT bio FROM users WHERE discord_id = ?", (self.discord_id,)
            )
            row = await cursor.fetchone()
            current_bio = row[0] if row and row[0] else "This user has no bio set."

        embed = discord.Embed(
            title="✏️ Edit Your Bio",
            description=f"**Current Bio:**\n{current_bio}\n\nUse the buttons below to edit or clear your bio.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click 'Edit Bio' to open the editor")

        view = BioEditView(self.discord_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Customize", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def customize_profile(self, interaction: discord.Interaction, button: ui.Button):
        if self.discord_id != interaction.user.id:
            return
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT profile_color FROM users WHERE discord_id = ?", (self.discord_id,)
            )
            row = await cursor.fetchone()
            current_color = row[0] if row and row[0] else "gold"

        embed = discord.Embed(
            title="🎨 Customize Your Profile",
            description=f"**Current Color:** {current_color}\n\nSelect a color from the dropdown below!",
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

async def build_profile_embed(
    discord_id: int,
    user: discord.User,
    balance: int,
    bio: str,
    color: discord.Color,
    greeting_time: str,
) -> discord.Embed:
    """Build the full profile embed including action stats."""
 
    embed = discord.Embed(
        title=f"good {greeting_time}, {user.name}!",
        description=bio,
        color=color,
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)
 
    # ── Action stats ──────────────────────────────────────────────────────────
    total = await get_total_actions_performed(discord_id)
    hugs = await get_received_count(discord_id, 'hug')
    pats = await get_received_count(discord_id, 'pat')

    embed.add_field(
        name="🎭 Total Actions Performed",
        value=str(total) if total > 0 else "none yet!",
        inline=True,
    )

    hug_text = f"{'1 time' if hugs == 1 else f'{hugs} times'}" if hugs > 0 else "none yet!"
    pat_text = f"{'1 time' if pats == 1 else f'{pats} times'}" if pats > 0 else "none yet!"

    embed.add_field(
        name="💝 Hugs & Pats",
        value=f"🤗 hugged: {hug_text}\n🫳 patted: {pat_text}",
        inline=True,
    )
    embed.set_footer(text="quacking good!")
    return embed
