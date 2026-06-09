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
    def __init__(self, user: discord.User, inbox_data: dict = None):
        super().__init__()
        # The other party in the conversation (not necessarily the one who clicked)
        self.user = user
        # If inbox_data is None, this is a fresh reply (no existing thread)
        self.inbox_data = inbox_data
        self.submitted = False
        self.input = discord.ui.TextInput(label="Your Reply", style=discord.TextStyle.paragraph, placeholder="Type your reply here...", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.submitted = True
        reply_message = self.input.value

        if not self.inbox_data:
            await interaction.response.send_message("Something went wrong — no inbox thread found.", ephemeral=True)
            return

        try:
            user = await interaction.client.fetch_user(self.inbox_data["user_id"])
            # owner_id may be NULL if no owner has claimed the thread yet
            owner_user = await interaction.client.fetch_user(self.inbox_data["owner_id"]) if self.inbox_data.get("owner_id") else None

            user_view = InboxView(user, self.inbox_data)
            owner_view = OwnerView(owner_user, self.inbox_data) if owner_user else None

            if await owner.is_owner(interaction.user.id):
                # Owner is replying → claim the thread if not already claimed, then DM the user
                await owner.claim_inbox_message(self.inbox_data["id"], interaction.user.id)
                await user.send(f"Reply from the bot developers:\n\n{reply_message}", view=user_view)
                await interaction.response.send_message("Your reply has been sent to the user.", ephemeral=True)
            else:
                # User is replying back → send embed to the owner who claimed the thread
                if not owner_user:
                    await interaction.response.send_message("No owner has responded to this thread yet.", ephemeral=True)
                    return
                user_info = await get_user_info(user.id)
                if not user_info:
                    # Fallback if the user has no DB record
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

    @discord.ui.button(label="Reply", style = discord.ButtonStyle.primary)
    async def reply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReplyModal(self.user, self.inbox_data)
        await interaction.response.send_modal(modal)
        await modal.wait()  # wait for the modal to close
        if modal.submitted:
            button.disabled = True
            await interaction.message.edit(view=self)


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
    
    @discord.ui.button(label="Mark as Resolved", style=discord.ButtonStyle.success)
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        inbox_id = self.inbox_data.get("id")
        is_updated = await owner.update_inbox_status(inbox_id=inbox_id, new_status="resolved")
        user = await interaction.client.fetch_user(self.inbox_data["user_id"])
        if is_updated:
            await user.send("Your message has been marked as resolved by the bot developers.")
            await owner.log_action(interaction, f"Message with ID {inbox_id} marked as resolved by owner {interaction.user.id}")
            await interaction.response.send_message("This message has been marked as resolved.", ephemeral=True)
            button.disabled = True
            await interaction.message.edit(view = self)
        else:
            await interaction.response.send_message("Failed to update the message status. Please try again later.", ephemeral=True)

