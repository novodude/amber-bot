import asyncio
import functools
import discord
import utils.userbase.owner as owner
from utils.userbase.database import get_user_info


def make_inbox_embed(user: discord.User ,user_info: dict, message: str) -> discord.Embed:
    embed = discord.Embed(title=f"New Message from {user.display_name}", description=message, color=0x00ff00)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.add_field(name="User discord ID", value=str(user.id), inline=False)
    embed.add_field(name="User ID", value=str(user_info.get("id",  "unknown")), inline=False)
    embed.add_field(name="Bio", value=user_info.get("bio", "unknown"), inline=False)
    embed.add_field(name="Level", value=str(user_info.get("level", 0)), inline=True)
    embed.add_field(name="Amber Dabloons", value=str(user_info.get("amber_dabloons", 0)), inline=True)
    embed.add_field(name="Total Actions", value=str(user_info.get("total_actions", 0)), inline=True)
    embed.add_field(name="TTT Wins", value=str(user_info.get("ttt_wins", 0)), inline=True)
    embed.add_field(name="TTT Streak", value=str(user_info.get("ttt_streak", 0)), inline=True)
    embed.add_field(name="Duck Clicker Score", value=str(user_info.get("duck_clicker_score", 0)), inline=True)
    return embed

class ReplyModal(discord.ui.Modal, title="Reply to User Message"):
    def __init__(self, user: discord.User, inbox_data: dict = None, button=None, message=None, parent_view=None):
        super().__init__()
        self.user = user
        self.inbox_data = inbox_data
        self.submitted = False
        self.button = button
        self.message = message
        self.parent_view = parent_view
        self.input = discord.ui.TextInput(label="Your Reply", style=discord.TextStyle.paragraph, placeholder="Type your reply here...", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.submitted = True
        reply_message = self.input.value

        # disable the reply button on the parent message
        if self.button and self.message and self.parent_view:
            self.button.disabled = True
            await self.message.edit(view=self.parent_view)

        if not self.inbox_data:
            await interaction.response.send_message("Something went wrong — no inbox thread found.", ephemeral=True)
            return

        try:
            data = await owner.get_inbox_message(self.inbox_data["id"])
            if not data:
                await interaction.response.send_message("This inbox thread no longer exists.", ephemeral=True)
                return

            self.inbox_data = data

            user = await interaction.client.fetch_user(self.inbox_data["user_id"])
            owner_user = await interaction.client.fetch_user(self.inbox_data["owner_id"]) if self.inbox_data.get("owner_id") else None

            user_view = InboxView(user, self.inbox_data)
            owner_view = OwnerView(owner_user, self.inbox_data) if owner_user else None

            if await owner.is_owner(interaction.user.id):
                if await owner.is_inbox_claimed(self.inbox_data["id"]) and self.inbox_data.get("owner_id") != interaction.user.id:
                    await interaction.response.send_message("This thread has already been claimed by another owner.", ephemeral=True)
                    return
                await owner.claim_inbox_message(self.inbox_data["id"], interaction.user.id)
                await user.send(
                    f"Reply from the bot developers:\n\n{reply_message}" + (f"\n\n— {owner_user.display_name}" if owner_user else ""),
                    view=user_view
                )
                await interaction.response.send_message("Your reply has been sent to the user.", ephemeral=True)
            else:
                if not owner_user:
                    await interaction.response.send_message("No owner has responded to this thread yet.", ephemeral=True)
                    return
                user_info = await get_user_info(user.id)
                if not user_info:
                    user_info = {"id": "unknown", "bio": "unknown", "level": 0, "amber_dabloons": 0,
                                 "total_actions": 0, "ttt_wins": 0, "ttt_streak": 0, "duck_clicker_score": 0}
                embed = make_inbox_embed(interaction.user, user_info, reply_message)
                await owner_user.send(embed=embed, view=owner_view)
                await interaction.response.send_message(f"Your reply has been sent to {owner_user.display_name}.", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("Failed to send the reply. The user may have privacy settings that prevent DMs.", ephemeral=True)

class InboxView(discord.ui.View):
    def __init__(self, user: discord.User, inbox_data: dict = None):
        super().__init__(timeout=None)
        self.user = user
        self.inbox_data = inbox_data

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.inbox_data:
            await interaction.response.send_message("Something went wrong — no inbox thread found.", ephemeral=True)
            return

        # re-fetch to get the latest status
        fresh_data = await owner.get_inbox_message(self.inbox_data["id"])
        if not fresh_data or fresh_data.get("status") == "resolved":
            await interaction.response.send_message("This conversation has been closed by the developers.", ephemeral=True)
            button.disabled = True
            await interaction.message.edit(view=self)
            return

        self.inbox_data = fresh_data
        modal = ReplyModal(self.user, self.inbox_data, button, interaction.message, self)
        await interaction.response.send_modal(modal)


class OwnerView(discord.ui.View):
    def __init__(self, user: discord.User, inbox_data: dict = None):
        super().__init__(timeout=None)
        self.user = user
        self.inbox_data = inbox_data

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReplyModal(self.user, self.inbox_data, button, interaction.message, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Mark as Resolved", style=discord.ButtonStyle.red)
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        inbox_id = self.inbox_data.get("id")
        is_updated = await owner.update_inbox_status(inbox_id=inbox_id, new_status="resolved")
        user = await interaction.client.fetch_user(self.inbox_data["user_id"])
        if is_updated:
            await user.send("Your message has been marked as resolved by the bot developers.")
            await owner.log_action(interaction, f"Message with ID {inbox_id} marked as resolved by owner {interaction.user.id}")
            await interaction.response.send_message("This message has been marked as resolved.", ephemeral=True)
            button.disabled = True
            button.style = discord.ButtonStyle.success
            button.label = "Resolved"
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("Failed to update the message status. Please try again later.", ephemeral=True)


class OwnerView(discord.ui.View):
    def __init__(self, user: discord.User, inbox_data: dict = None):
        super().__init__(timeout = None)
        self.user = user
        self.inbox_data = inbox_data

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReplyModal(self.user, self.inbox_data)
        await interaction.response.send_modal(modal)
        await modal.wait()  # wait for the modal to close
        if modal.submitted:
            button.disabled = True
            await interaction.message.edit(view=self)
    
    @discord.ui.button(label="Mark as Resolved", style=discord.ButtonStyle.red)
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        inbox_id = self.inbox_data.get("id")
        is_updated = await owner.update_inbox_status(inbox_id=inbox_id, new_status="resolved")
        user = await interaction.client.fetch_user(self.inbox_data["user_id"])
        if is_updated:
            await user.send("Your message has been marked as resolved by the bot developers.")
            await owner.log_action(interaction, f"Message with ID {inbox_id} marked as resolved by owner {interaction.user.id}")
            await interaction.response.send_message("This message has been marked as resolved.", ephemeral=True)
            button.disabled = True
            button.style = discord.ButtonStyle.success
            button.label = "Resolved"
            await interaction.message.edit(view = self)
        else:
            await interaction.response.send_message("Failed to update the message status. Please try again later.", ephemeral=True)

            


DELETE_EMOJI = ["🗑️", "🗑"]

async def handle_delete_reply(bot, message: discord.Message):
    if not message.reference:
        return
    if message.content not in DELETE_EMOJI:
        return

    try:
        replied_to = message.reference.resolved
        if replied_to is None:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        return

    if replied_to.author.id != bot.user.id:
        return

    try:
        await replied_to.delete()
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
