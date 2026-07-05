import discord
import aiosqlite
from discord import ui
from utils.userbase.database import clear_bio, get_bio, get_profile_data, has_custom_color, set_bio, set_profile_color
from utils.userbase.owner import is_owner
from utils.economy import get_dabloons
from utils.userbase.database import get_user_id_from_discord
from utils.action_counts import get_total_actions_performed, get_received_count

class ColorSelect(ui.Select):
    def __init__(self, profile_view: 'ProfileView'):
        self.profile_view = profile_view
        options = [
            discord.SelectOption(label="Gold",      emoji="🟡", value="gold",      description="Classic gold color"),
            discord.SelectOption(label="Blue",      emoji="🔵", value="blue",      description="Cool blue"),
            discord.SelectOption(label="Red",       emoji="🔴", value="red",       description="Bold red"),
            discord.SelectOption(label="Green",     emoji="🟢", value="green",     description="Fresh green"),
            discord.SelectOption(label="Purple",    emoji="🟣", value="purple",    description="Royal purple"),
            discord.SelectOption(label="Orange",    emoji="🟠", value="orange",    description="Vibrant orange"),
            discord.SelectOption(label="Pink",      emoji="💖", value="pink",      description="Lovely pink"),
            discord.SelectOption(label="Dark Blue", emoji="🌊", value="dark_blue", description="Deep ocean blue"),
            # shop-unlocked colors
            discord.SelectOption(label="Cyan",      emoji="🩵", value="cyan",      description="Unlockable from shop"),
            discord.SelectOption(label="Rose",      emoji="🌸", value="rose",      description="Unlockable from shop"),
            discord.SelectOption(label="Midnight",  emoji="🌑", value="midnight",  description="Unlockable from shop"),
            # custom hex — only shows effect if the user has set one
            discord.SelectOption(label="Custom",    emoji="🎨", value="custom",    description="Your custom hex color"),
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

        # For "custom" we just switch to it — the hex is already stored from the shop modal.
        # If they haven't set one yet, it falls back to gold gracefully.
        await set_profile_color(user_id, color_value)

        label = color_value.replace('_', ' ').title()
        embed = discord.Embed(
            title="Profile Color Updated",
            description=f"Your profile color has been updated to **{label}**.",
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
        await set_bio(user_id, new_bio)
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
        await clear_bio(interaction.user.id)
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

    def get_color(self, color_name: str, custom_hex: str | None = None) -> discord.Color:
        """
        Resolve a color name to a discord.Color.
        Handles the full set of default + shop-unlocked + custom hex colors.
        Falls back to gold if unknown.
        """
        colors = {
            "gold":      discord.Color.gold(),
            "blue":      discord.Color.blue(),
            "red":       discord.Color.red(),
            "green":     discord.Color.green(),
            "purple":    discord.Color.purple(),
            "orange":    discord.Color.orange(),
            "pink":      discord.Color.from_rgb(255, 192, 203),
            "dark_blue": discord.Color.dark_blue(),
            # shop-unlocked
            "cyan":      discord.Color.from_rgb(0, 210, 220),
            "rose":      discord.Color.from_rgb(220, 80, 120),
            "midnight":  discord.Color.from_rgb(20, 20, 40),
        }

        if color_name == "custom":
            if custom_hex:
                try:
                    return discord.Color.from_str(custom_hex)
                except Exception:
                    pass
            return discord.Color.gold()  # fallback if hex is missing/malformed

        return colors.get(color_name, discord.Color.gold())

    async def refresh_profile(self, interaction: discord.Interaction):
        profile_data = await get_profile_data(interaction.user.id)
        bio        = profile_data.get('bio', "This user has no bio set.")
        color_name = profile_data.get('profile_color', "gold")
        custom_hex = profile_data.get('custom_hex_color', None)

        balance = await get_dabloons(await get_user_id_from_discord(self.discord_id))

        if await is_owner(self.discord_id):
            greeting = "Look it's the owner of Amber! 👑"
        else:
            greeting = f"hello there, duckling!"

        embed = await build_profile_embed(
            discord_id=self.discord_id,
            user=interaction.user,
            balance=balance,
            bio=bio,
            color=self.get_color(color_name, custom_hex),
            greeting=greeting,
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
        current_bio = await get_bio(self.discord_id)
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
            profile_data = await get_profile_data(self.discord_id)
            current_color = profile_data.get('profile_color', 'gold')
            custom_hex    = profile_data.get('custom_hex_color', None)

        label = current_color.replace('_', ' ').title()
        desc = f"**Current Color:** {label}"
        if current_color == "custom" and custom_hex:
            desc += f" (`{custom_hex}`)"
        desc += "\n\nSelect a color from the dropdown below!"

        embed = discord.Embed(
            title="🎨 Customize Your Profile",
            description=desc,
            color=self.get_color(current_color, custom_hex)
        )

        customize_view = ui.View(timeout=60)
        customize_view.add_item(ColorSelect(self))

        # Show "Change Custom Color" button only if they've unlocked it
        has_custom = await has_custom_color(self.discord_id)

        if has_custom:
            from commands.shop import HexColorModal
            change_hex_button = ui.Button(label="Change Custom Color", style=discord.ButtonStyle.primary, emoji="🎨", row=1)

            async def change_hex_callback(button_interaction: discord.Interaction):
                if button_interaction.user.id != self.discord_id:
                    await button_interaction.response.send_message("This isn't your profile!", ephemeral=True)
                    return
                user_id_db = await get_user_id_from_discord(self.discord_id)
                await button_interaction.response.send_modal(HexColorModal(user_id_db))

            change_hex_button.callback = change_hex_callback
            customize_view.add_item(change_hex_button)

        back_button = ui.Button(label="Back to Profile", style=discord.ButtonStyle.secondary, emoji="🔙", row=1)

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
    greeting: str,
) -> discord.Embed:
    """Build the full profile embed including action stats."""

    embed = discord.Embed(
        title=f"{greeting}, {user.name}",
        description=bio,
        color=color,
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Dabloons Balance", value=f"🪙 {balance} dabloons", inline=False)

    # ── Action stats ──────────────────────────────────────────────────────────
    total = await get_total_actions_performed(discord_id)
    hugs  = await get_received_count(discord_id, 'hug')
    pats  = await get_received_count(discord_id, 'pat')

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
