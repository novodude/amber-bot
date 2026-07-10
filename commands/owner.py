from datetime import datetime
from discord.ext import commands
import utils.userbase.owner as owner_utils
import utils.userbase.database as database
from utils.userbase.database import DB_PATH, get_user_id_from_discord, get_user_info
import utils.amber as amber_utils
from utils.amber import InboxView
from discord import app_commands
from utils import economy
import aiosqlite
import functools
import asyncio
import discord

def is_owner(function):
    @functools.wraps(function)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        if not await owner_utils.is_owner(interaction.user.id):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        return await function(self, interaction, *args, **kwargs)
    return wrapper


def build_username_sync_embed(
    updated: int,
    skipped: int,
    total: int,
    last_username: str | None,
    done: bool = False,
    error: str | None = None,
) -> discord.Embed:
    if error:
        return discord.Embed(
            title="❌ Username Sync Failed",
            description=error,
            color=discord.Color.red(),
        )
 
    if done:
        embed = discord.Embed(
            title="✅ Username Sync Complete",
            description=f"Checked **{total}** users in the database.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Updated", value=str(updated), inline=True)
        embed.add_field(name="Skipped", value=str(skipped), inline=True)
        return embed
 
    processed = updated + skipped
    if total > 0:
        filled = int((processed / total) * 20)
        bar = "█" * filled + "░" * (20 - filled)
        progress_text = f"`{bar}` {processed}/{total}"
    else:
        progress_text = "no users to process"
 
    embed = discord.Embed(
        title="🔄 Syncing Usernames",
        description=progress_text,
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Updated", value=str(updated), inline=True)
    embed.add_field(name="Skipped", value=str(skipped), inline=True)
    if last_username:
        embed.add_field(name="Last updated", value=last_username, inline=False)
    embed.set_footer(text="Running in the background — you can keep using the bot")
    return embed

USERNAME_SYNC_UPDATE_EVERY = 5   # db is small — update progress every 5 users
USERNAME_SYNC_DELAY = 1          # seconds between fetch_user() calls

async def sync_usernames_background(
    *,
    bot,
    progress_message: discord.Message,
    requester: discord.User,
):
    """
    Walks every discord_id in the users table, re-fetches their current
    Discord username via bot.fetch_user(), and updates the username column.
    Skips (and counts) users who can't be fetched — left Discord, deactivated,
    or otherwise unreachable — rather than aborting the whole run.
    """
    updated = 0
    skipped = 0
    last_username: str | None = None
 
    async def edit_progress(done=False, error=None):
        try:
            embed = build_username_sync_embed(
                updated=updated,
                skipped=skipped,
                total=total,
                last_username=last_username,
                done=done,
                error=error,
            )
            await progress_message.edit(embed=embed)
        except Exception:
            pass
 
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT discord_id FROM users")
            rows = await cursor.fetchall()
 
        discord_ids = [row[0] for row in rows]
        total = len(discord_ids)
 
        if total == 0:
            await edit_progress(error="No users found in the database.")
            return
 
        await edit_progress()  # show 0/total right away
 
        async with aiosqlite.connect(DB_PATH) as db:
            for discord_id in discord_ids:
                try:
                    user = await bot.fetch_user(discord_id)
                except (discord.NotFound, discord.HTTPException):
                    skipped += 1
                else:
                    await db.execute(
                        "UPDATE users SET username = ? WHERE discord_id = ?",
                        (user.display_name, discord_id)
                    )
                    await db.commit()
                    updated += 1
                    last_username = user.display_name
 
                processed = updated + skipped
                if processed % USERNAME_SYNC_UPDATE_EVERY == 0:
                    await edit_progress()
 
                await asyncio.sleep(USERNAME_SYNC_DELAY)
 
        await edit_progress(done=True)
 
        # DM the owner who triggered it when complete
        try:
            dm_embed = discord.Embed(
                title="✅ Username Sync Complete!",
                description=f"Checked **{total}** users.",
                color=discord.Color.green(),
            )
            dm_embed.add_field(name="Updated", value=str(updated), inline=True)
            dm_embed.add_field(name="Skipped", value=str(skipped), inline=True)
            await requester.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # DMs closed, no big deal
 
    except Exception as e:
        await edit_progress(error=str(e))

class SuggestionModal(discord.ui.Modal, title="Submit a Suggestion"):
    suggestion = discord.ui.TextInput(
        label="Your suggestion",
        style=discord.TextStyle.paragraph,
        placeholder="Write your suggestion here...",
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        inbox_id = await owner_utils.create_inbox_message(interaction.user.id, self.suggestion.value, interaction)
        inbox_data = await owner_utils.get_inbox_message(inbox_id)

        owners = await owner_utils.list_users()

        if inbox_data:
            user_info = await database.get_user_info(interaction.user.id) or {
                "id": "unknown", "bio": "unknown", "level": 0, "amber_dabloons": 0,
                "total_actions": 0, "ttt_wins": 0, "ttt_streak": 0, "duck_clicker_score": 0
            }
            embed = amber_utils.make_inbox_embed(interaction.user, user_info, self.suggestion.value)
            owner_view = amber_utils.OwnerView(interaction.user, inbox_data)
            for owner_id in owners:
                try:
                    owner_user = await interaction.client.fetch_user(owner_id)
                    await owner_user.send(embed=embed, view=owner_view)
                except discord.Forbidden:
                    continue  # Skip if the owner has DMs disabled

        await interaction.response.send_message("Suggestion submitted, thanks! 🤍", ephemeral=True)

class UpdateView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Stop Update Messages", style=discord.ButtonStyle.danger)
    async def stop_updates(self, interaction: discord.Interaction, button: discord.ui.Button):
        already_muted = await database.check_update_muted(self.user_id)
        if already_muted:
            await interaction.response.send_message("You're already unsubscribed from update messages.", ephemeral=True)
            return
        await database.switch_update_muted(self.user_id)
        await interaction.response.send_message("You've been unsubscribed from update messages.", ephemeral=True)

    @discord.ui.button(label="Add a Suggestion", style=discord.ButtonStyle.secondary)
    async def add_suggestion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())

class ListInboxView(discord.ui.View):
    def __init__(self, inbox_messages):
        super().__init__(timeout=None)
        self.inbox_messages = inbox_messages
        self.page = 0
        self.page_size = 5
        self.update_buttons()

    @property
    def total_pages(self):
        return max(1, (len(self.inbox_messages) + self.page_size - 1) // self.page_size)

    def build_embed(self):
        start = self.page * self.page_size
        chunk = self.inbox_messages[start:start + self.page_size]
        embed = discord.Embed(title=f"Inbox — Page {self.page + 1}/{self.total_pages}")
        for msg in chunk:
            user = f"<@{msg['user_id']}>"
            id = msg['id']
            status = msg['status']
            timestamp = msg['timestamp']
            preview = msg['message'][:50] + ("..." if len(msg['message']) > 50 else "")
            embed.add_field(
                name=f"Id: {id} | {user} · {status} · {timestamp}",
                value=preview,
                inline=False
            )
        return embed

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            prev_btn = discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary)
            prev_btn.callback = self.previous
            self.add_item(prev_btn)
        if self.page < self.total_pages - 1:
            next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.primary)
            next_btn.callback = self.next
            self.add_item(next_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await owner_utils.is_owner(interaction.user.id)

    async def previous(self, interaction: discord.Interaction, button=None):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next(self, interaction: discord.Interaction, button=None):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

def make_user_embed(user: discord.User, user_info: dict):
    embed = discord.Embed(
        title=f"data of {user.display_name}:",
        description=user_info.get('bio', "no bio is set"),
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.add_field(name="User discord ID", value=str(user.id), inline=False)
    embed.add_field(name="User ID", value=str(user_info.get("id",  "unknown")), inline=False)
    embed.add_field(name="Level", value=str(user_info.get("level", 0)), inline=True)
    embed.add_field(name="Amber Dabloons", value=str(user_info.get("amber_dabloons", 0)), inline=True)
    embed.add_field(name="Total Actions", value=str(user_info.get("total_actions", 0)), inline=True)
    embed.add_field(name="TTT Wins", value=str(user_info.get("ttt_wins", 0)), inline=True)
    embed.add_field(name="TTT Streak", value=str(user_info.get("ttt_streak", 0)), inline=True)
    embed.add_field(name="Duck Clicker Score", value=str(user_info.get("duck_clicker_score", 0)), inline=True)

    return embed

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class OwnerCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="owner",
            description="Commands for the bot owner.",
            guild_only=True,
        )


    @app_commands.command(name="exec", description="Execute a shell command and return output.")
    @app_commands.describe(command="The shell command to run")
    @is_owner
    async def exec_cmd(self, interaction: discord.Interaction, command: str):
        
        await interaction.response.defer()
        
        try:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
            
            output = stdout.decode() or stderr.decode() or "No output."
            
            if len(output) > 1900:
                output = output[:1900] + "\n... (truncated)"
            
            await interaction.followup.send(f"```\n{output}\n```")
        
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Command timed out.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="get_user", description="get user info and stats")
    @app_commands.describe(user="the user you want to search")
    @is_owner
    async def get_user(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        user_info = await get_user_info(user.id)

        if user_info is None:
            await interaction.followup.send("User is not is the system.", ephemeral=True)
            return

        embed = make_user_embed(user, user_info)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="list_inbox", description="List all inbox messages.")
    @is_owner
    async def list_inbox(self, interaction: discord.Interaction):
        inbox_messages = await owner_utils.list_inbox_messages()
        if not inbox_messages:
            await interaction.response.send_message("No inbox messages found.", ephemeral=True)
            return
        
        view = ListInboxView(inbox_messages)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

    @app_commands.command(name="claim_inbox", description="Claim an inbox message by ID.")
    @app_commands.describe(inbox_id="The ID of the inbox message to claim.", reply="Your reply to the inbox message.")
    @is_owner
    async def claim_inbox(self, interaction: discord.Interaction, inbox_id: int, reply: str):
        if await owner_utils.is_inbox_claimed(inbox_id):
            await interaction.response.send_message(f"Inbox message {inbox_id} is already claimed.", ephemeral=True)
            return

        await owner_utils.claim_inbox_message(inbox_id, interaction.user.id)
        await owner_utils.update_inbox_status(inbox_id, "claimed")
        
        data = await owner_utils.get_inbox_message(inbox_id)
        if not data:
            await interaction.response.send_message(f"Inbox message {inbox_id} not found.", ephemeral=True)
            return
        
        user = await interaction.client.fetch_user(data['user_id'])
        if not user:
            await interaction.response.send_message(f"User with ID {data['user_id']} not found.", ephemeral=True)
            return

        user_view = InboxView(user, data)
        try:
                await user.send(f"Reply from the bot developers:\n\n{reply}\n\n{interaction.user.display_name}", view=user_view)
        except discord.Forbidden:
            await interaction.response.send_message(f"Could not send a reply to user {user}. They might have DMs disabled.", ephemeral=True)
            return

        await owner_utils.log_action(interaction, f"Owner {interaction.user.id} claimed inbox message {inbox_id} and sent a reply.")
        await interaction.response.send_message(f"You have claimed inbox message {inbox_id} and sent your reply.", ephemeral=True)

    @app_commands.command(name="userbase", description="Show userbase statistics.")
    @is_owner
    async def userbase(self, interaction: discord.Interaction):
        stats = await database.get_userbase_stats()
        embed = discord.Embed(title="Userbase Statistics")
        embed.add_field(name="Total Users", value=str(stats['total_users']), inline=False)
        embed.add_field(name="Average Level", value=f"{stats['average_level']:.2f}", inline=False)
        embed.add_field(name="Total Dabloons", value=str(stats['total_dabloons']), inline=False)
        embed.add_field(name="Average Dabloons", value=f"{stats['average_dabloons']:.2f}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="give_dabloons", description="Give dabloons to a user/s.")
    @app_commands.describe(
            user="The user to give dabloons to.",
            amount="The amount of dabloons to give.",
            everyone="Whether to give dabloons to everyone.",
            reason="The reason for giving dabloons."
    )
    @is_owner
    async def give_dabloons(self, interaction: discord.Interaction, user: discord.User = None, amount: int = 0, everyone: bool = False, reason: str = "No reason provided"):
        if not user and not everyone:
            await interaction.response.send_message("You must specify a user or set 'evryone' to True.", ephemeral=True)
            return

        if everyone:
            await economy.add_dabloons_to_all(amount)
            await interaction.response.send_message(f"Gave {amount} dabloons to all users. Reason: {reason}", ephemeral=True)
        else:
            user_id = await get_user_id_from_discord(user.id)
            if not user_id:
                await interaction.response.send_message(f"User {user} is not registered in the database.", ephemeral=True)
                return
            await economy.add_dabloons(user_id, amount)
            await user.send(f"You have received {amount} dabloons from the bot owner.\nReason:\n {reason}")
        await owner_utils.log_action(interaction, f"Owner {interaction.user.id} gave {amount} dabloons to {'everyone' if everyone else user}.\n Reason: {reason}")
        await interaction.response.send_message(f"Gave {amount} dabloons to {'everyone' if everyone else user}. Reason: {reason}", ephemeral=True)

    @app_commands.command(name="set_log_channel", description="Set the log channel for owner commands.")
    @app_commands.describe(channel="The channel to set as the log channel.")
    @is_owner
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await owner_utils.set_log_channel(channel.id)
        await interaction.response.send_message(f"Log channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set_update_channel", description=" Set the update channel for update messages.")
    @app_commands.describe(channel="The channel to set as the update channel.")
    @is_owner
    async def set_update_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await owner_utils.set_update_channel(channel.id)
        await interaction.response.send_message(f"Update channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="sync_usernames", description="Re-fetch and update stored usernames for all registered users.")
    @is_owner
    async def sync_usernames(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
 
        progress_embed = build_username_sync_embed(
            updated=0, skipped=0, total=0, last_username=None
        )
        progress_msg = await interaction.followup.send(
            content="🔄 Syncing usernames in the background...",
            embed=progress_embed,
        )
 
        asyncio.create_task(sync_usernames_background(
            bot=interaction.client,
            progress_message=progress_msg,
            requester=interaction.user,
        ))
        
        log = f"syncing database usernames...\nrequested by `{interaction.user.id}`"
        await owner_utils.log_action(interaction, log)


async def updates_handler(bot: commands.Bot, message: discord.Message):
    if message.author.bot:
        return
    update_channel_id = await owner_utils.get_update_channel()
    if not message.channel.id == update_channel_id:
        return
    await message.add_reaction("🦆")
    users = await database.list_users()
    failed = 0
    for user_id in users:
        try:
            user = await bot.fetch_user(user_id)
            view = UpdateView(user_id)
            if not await database.check_update_muted(user_id):
                files = [await attachment.to_file() for attachment in message.attachments]
                await user.send(
                    content=message.content or None,
                    files=files,
                    view=view
                )
                await asyncio.sleep(1)
            else:
                failed += 1
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException:
            failed += 1
            await asyncio.sleep(3)
    log_channel_id = await owner_utils.get_log_channel()
    if failed:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"Broadcast done. Failed to DM {failed} users.")


async def owner_setup(bot):
    bot.tree.add_command(OwnerCommands())
