import datetime
import traceback
import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
from utils.userbase.database import DB_PATH



class WelcomeMessageModal(discord.ui.Modal, title="Set Welcome Message"):
    message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Welcome {user} to {server}!",
        required=True,
        max_length=500
    )

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_config (guild_id, welcome_channel_id, welcome_message)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    welcome_channel_id=excluded.welcome_channel_id,
                    welcome_message=excluded.welcome_message
            """, (interaction.guild_id, self.channel.id, str(self.message)))
            await db.commit()

        await interaction.response.send_message(
            f"Welcome message set! Messages will be sent in {self.channel.mention}",
            ephemeral=True
        )


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Catches all app command errors in this cog and sends a user-friendly message
    # Also prints the full traceback to console for debugging
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        traceback.print_exception(type(error), error, error.__traceback__)

        if isinstance(error, app_commands.MissingPermissions):
            message = "You don't have permission to use this command"
        else:
            message = f"An error occurred: {str(error)}"

        # Try sending as a new response first; fall back to followup if already deferred
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except:
            await interaction.followup.send(message, ephemeral=True)

    # Shared safety check before any moderation action.
    # Returns True if the bot can moderate the target member, False otherwise (and sends an error message).
    async def can_moderate_member(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        # guild check must come before guild.me check to avoid AttributeError on None
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return False

        # Bot isn't a member of the server (e.g. user-installed app used in foreign guild)
        if interaction.guild.me is None:
            await interaction.response.send_message(
                "I need to be a member of this server to moderate members!",
                ephemeral=True
            )
            return False

        # Prevent self-moderation
        if member == interaction.user:
            await interaction.response.send_message("You can't moderate yourself!", ephemeral=True)
            return False

        # Discord doesn't allow bots to action the server owner
        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message("I cannot moderate the server owner!", ephemeral=True)
            return False

        # Compare role hierarchy positions — bot must be above the target member
        bot_top = interaction.guild.me.top_role.position if interaction.guild.me.top_role else 0
        member_top = member.top_role.position if member.top_role else 0

        if member_top >= bot_top:
            await interaction.response.send_message(
                "I cannot moderate this member because their role is higher than or equal to mine!",
                ephemeral=True
            )
            return False

        return True

    # Builds a consistent embed used across kick, ban, timeout, etc.
    def create_mod_embed(
        self,
        member: discord.Member,
        interaction: discord.Interaction,
        title: str,
        reason: str = None,
        color: discord.Color = discord.Color.red()
    ) -> discord.Embed:
        today = discord.utils.utcnow()

        description = f"**Reason:**\n{reason or 'No reason provided'}"

        # joined_at can be None if member data isn't fully cached
        if member.joined_at:
            days = (today - member.joined_at).days
            description = f"They were in the server for **{days} days**\n{description}"

        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        if member.joined_at:
            embed.add_field(
                name="Joined Server",
                value=discord.utils.format_dt(member.joined_at, style='R'),
                inline=True
            )

        embed.add_field(
            name="Action Time",
            value=discord.utils.format_dt(today, style='d'),
            inline=True
        )

        return embed

    # Fetches the log channel for a guild and sends the embed to it.
    # Silently does nothing if no log channel is set or the channel no longer exists.
    async def send_log(self, guild_id: int, embed: discord.Embed):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT log_channel_id FROM guild_config WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            return  # No log channel configured

        channel = self.bot.get_channel(row[0])
        if not channel:
            return  # Channel was deleted or bot lost access

        await channel.send(embed=embed)

    # Inserts a warning record into the database
    async def log_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO warnings (user_id, guild_id, moderator_id, reason)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, moderator_id, reason))
            await db.commit()

    # Fetches all warnings for a user in a guild, ordered newest first
    async def get_warnings(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT moderator_id, reason, timestamp
                FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY timestamp DESC
            """, (guild_id, user_id))
            return await cursor.fetchall()

    # Removes all warnings for a user in a guild
    async def delete_warnings(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                DELETE FROM warnings
                WHERE guild_id = ? AND user_id = ?
            """, (guild_id, user_id))
            await db.commit()

    admin = app_commands.Group(name="admin", description="Collection of admin commands")
    server = app_commands.Group(name="server", description="Collection of server management commands")


    ##################
    # Server Commands #
    ##################

    @server.command(name="info", description="Get information about the server")
    @app_commands.guild_only()
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 {guild.name} Information",
            description=guild.description or "No description provided.",
            color=discord.Color.blue()
        )

        # Count text and voice channels separately
        text_channels_count = sum(1 for c in guild.channels if isinstance(c, discord.TextChannel))
        voice_channels_count = sum(1 for c in guild.channels if isinstance(c, discord.VoiceChannel))

        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name="Owner", value=guild.owner, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=f"{text_channels_count} Text | {voice_channels_count} Voice", inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Created On", value=discord.utils.format_dt(guild.created_at, style='d'), inline=True)
        await interaction.response.send_message(embed=embed)

    @server.command(name="invite", description="Get an invite link for the server")
    @app_commands.guild_only()
    async def invite(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return

        # Creates a single-use invite valid for 1 hour via the first text channel
        invite = await guild.text_channels[0].create_invite(max_age=3600, max_uses=1, reason=f"Invite requested by {interaction.user}")
        await interaction.response.send_message(f"Here's an invite link for the server (valid for 1 hour): {invite.url}", ephemeral=True)

    @server.command(name="icon", description="Get the server's icon")
    @app_commands.guild_only()
    async def icon(self, interaction: discord.Interaction):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return

        if guild.icon:
            embed = discord.Embed(title=f"{guild.name}'s Icon", color=discord.Color.blue())
            embed.set_image(url=guild.icon.url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("This server doesn't have an icon!", ephemeral=True)

    @server.command(name="banner", description="Get the server's banner")
    @app_commands.guild_only()
    async def banner(self, interaction: discord.Interaction):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
            return

        if guild.banner:
            embed = discord.Embed(title=f"{guild.name}'s Banner", color=discord.Color.blue())
            embed.set_image(url=guild.banner.url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("This server doesn't have a banner!", ephemeral=True)

    @server.command(name="set_prefix", description="Set a custom command prefix for the server")
    @app_commands.describe(prefix="The new command prefix (1-5 characters)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_prefix(self, interaction: discord.Interaction, prefix: str):
        if len(prefix) < 1 or len(prefix) > 5:
            await interaction.response.send_message("Please provide a prefix between 1 and 5 characters long.", ephemeral=True)
            return

        # Upsert the prefix — insert if guild has no config row, otherwise update just the prefix
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_config (guild_id, prefix)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET prefix=excluded.prefix
            """, (interaction.guild_id, prefix))
            await db.commit()

        await interaction.response.send_message(f"Command prefix has been set to `{prefix}` for this server!", ephemeral=True)

        # Log the config change
        log_embed = discord.Embed(
            title="⚙️ Prefix Updated",
            description=f"**New prefix:** `{prefix}`",
            color=discord.Color.blurple()
        )
        log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        log_embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
        await self.send_log(interaction.guild_id, log_embed)

    @server.command(name="set_welcome", description="Set a channel for welcome messages")
    @app_commands.describe(channel="The channel to send welcome messages in")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                "I don't have permission to send messages in that channel!",
                ephemeral=True
            )
            return

        # Send the modal — Discord opens a popup form for the user to fill in
        await interaction.response.send_modal(WelcomeMessageModal(channel))

    @server.command(name="set_welcome_off", description="Disable welcome messages")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_welcome_off(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE guild_config
                SET welcome_channel_id = NULL
                WHERE guild_id = ?
            """, (interaction.guild_id,))
            await db.commit()

        await interaction.response.send_message("Welcome messages have been disabled for this server.", ephemeral=True)

        # Log the config change
        log_embed = discord.Embed(
            title="⚙️ Welcome Messages Disabled",
            color=discord.Color.blurple()
        )
        log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        log_embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
        await self.send_log(interaction.guild_id, log_embed)


    @server.command(name="set_autorole", description="Set a role to automatically assign to new members")
    @app_commands.describe(role="The role to assign to new members")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        # Make sure the bot's role is above the autorole in the hierarchy
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(
                "I can't assign that role — it's higher than or equal to my highest role!",
                ephemeral=True
            )
            return

        # Don't allow assigning @everyone
        if role.is_default():
            await interaction.response.send_message("You can't set @everyone as the autorole!", ephemeral=True)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_config (guild_id, autorole_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET autorole_id=excluded.autorole_id
            """, (interaction.guild_id, role.id))
            await db.commit()

        await interaction.response.send_message(f"New members will now automatically receive the {role.mention} role!", ephemeral=True)

        log_embed = discord.Embed(
            title="⚙️ Autorole Set",
            description=f"**Role:** {role.mention}",
            color=discord.Color.blurple()
        )
        log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        log_embed.add_field(name="Set At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
        await self.send_log(interaction.guild_id, log_embed)

    @server.command(name="set_autorole_off", description="Disable autorole for new members")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_autorole_off(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE guild_config SET autorole_id = NULL WHERE guild_id = ?
            """, (interaction.guild_id,))
            await db.commit()

        await interaction.response.send_message("Autorole has been disabled.", ephemeral=True)

        log_embed = discord.Embed(title="⚙️ Autorole Disabled", color=discord.Color.blurple())
        log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await self.send_log(interaction.guild_id, log_embed)

    @server.command(name="set_log", description="Set a channel for moderation logs")
    @app_commands.describe(channel="The channel to send moderation logs in")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_log(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Verify the bot can actually send in the chosen channel before saving
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                "I don't have permission to send messages in that channel! Please choose a different channel or adjust my permissions.",
                ephemeral=True
            )
            return

        # Upsert log channel — only updates log_channel_id, leaves other config columns untouched
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_config (guild_id, log_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id
            """, (interaction.guild_id, channel.id))
            await db.commit()

        await interaction.response.send_message(f"Moderation logs will now be sent in {channel.mention}!", ephemeral=True)

        # Send a test message to confirm the log channel is working
        log_embed = discord.Embed(
            title="✅ Log Channel Set",
            description="Moderation logs will now be sent here.",
            color=discord.Color.green()
        )
        log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        log_embed.add_field(name="Set At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
        await self.send_log(interaction.guild_id, log_embed)
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT welcome_channel_id, welcome_message, autorole_id FROM guild_config WHERE guild_id = ?",
                (member.guild.id,)
            )
            row = await cursor.fetchone()

        if not row:
            return

        # Send welcome message
        if row[0]:
            channel = member.guild.get_channel(row[0])
            if channel:
                message = (row[1] or "Welcome {user} to {server}!") \
                    .replace("{user}", member.mention) \
                    .replace("{server}", member.guild.name)
                await channel.send(message)

    # Assign autorole
    if row[2]:
        role = member.guild.get_role(row[2])
        if role:
            try:
                await member.add_roles(role, reason="Autorole")
            except discord.Forbidden:
                pass  # Bot lost permission or role was moved above it


    ##################
    # Admin Commands #
    ##################

    @admin.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not await self.can_moderate_member(interaction, member):
            return

        await interaction.response.defer()

        try:
            embed = self.create_mod_embed(
                member=member,
                interaction=interaction,
                title=f"👢 {member.name} was kicked",
                reason=reason,
                color=discord.Color.red()
            )
            await member.kick(reason=f"{reason} | Kicked by {interaction.user}")
            await interaction.followup.send(embed=embed)
            await self.send_log(interaction.guild_id, embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to kick members!", ephemeral=True)

    @admin.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="Member to ban", reason="Reason for the ban")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not await self.can_moderate_member(interaction, member):
            return

        await interaction.response.defer()

        try:
            embed = self.create_mod_embed(
                member=member,
                interaction=interaction,
                title=f"🔨 {member.name} was banned",
                reason=reason,
                color=discord.Color.red()
            )
            await member.ban(reason=f"{reason} | Banned by {interaction.user}")
            await interaction.followup.send(embed=embed)
            await self.send_log(interaction.guild_id, embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to ban members!", ephemeral=True)

    @admin.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for the unban")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        # Validate before deferring so we can send an ephemeral error without deferring first
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message("Please provide a valid numerical user ID.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            banned_user = await self.bot.fetch_user(user_id_int)
            await interaction.guild.unban(banned_user, reason=f"{reason} | Unbanned by {interaction.user}")

            embed = discord.Embed(
                title=f"✅ {banned_user.name} was unbanned",
                description=f"**Reason:**\n{reason or 'No reason provided'}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=banned_user.display_avatar.url)
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)
            await self.send_log(interaction.guild_id, embed)

        except discord.NotFound:
            await interaction.followup.send("This user is not banned or doesn't exist!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to unban members!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @admin.command(name="timeout", description="Timeout a member for a specified duration")
    @app_commands.describe(
        member="Member to timeout",
        duration="Duration (e.g. 10m, 1h, 1d)",
        reason="Reason for the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = None):
        if not await self.can_moderate_member(interaction, member):
            return

        # Parse duration string (e.g. "10m", "2h", "1d") into total seconds
        time_multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit = duration[-1].lower()
            if unit not in time_multiplier:
                raise ValueError("Invalid unit")
            amount = int(duration[:-1])
            if amount <= 0:
                raise ValueError("Amount must be positive")
            timeout_seconds = amount * time_multiplier[unit]
        except Exception:
            await interaction.response.send_message(
                "Invalid duration format! Use something like `10m`, `1h`, or `1d`.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            embed = self.create_mod_embed(
                member=member,
                interaction=interaction,
                title=f"🔇 {member.name} was timed out for {duration}",
                reason=reason,
                color=discord.Color.orange()
            )
            # Pass a timedelta directly — member.timeout() expects a duration, not an absolute datetime
            await member.timeout(
                datetime.timedelta(seconds=timeout_seconds),
                reason=f"{reason} | Timed out by {interaction.user}"
            )
            await interaction.followup.send(embed=embed)
            await self.send_log(interaction.guild_id, embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to timeout members!", ephemeral=True)

    @admin.command(name="warn", description="Warn a member in the server")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guild_only()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not await self.can_moderate_member(interaction, member):
            return

        await interaction.response.defer()

        try:
            await self.log_warning(interaction.guild_id, member.id, interaction.user.id, reason or "No reason provided")
            embed = discord.Embed(
                title=f"⚠️ {member.name} was warned",
                description=f"**Reason:**\n{reason or 'No reason provided'}",
                color=discord.Color.yellow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.followup.send(embed=embed)
            await self.send_log(interaction.guild_id, embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred while logging the warning: {str(e)}", ephemeral=True)

    @admin.command(name="warnings", description="View warnings for a member")
    @app_commands.describe(member="Member to view warnings for")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guild_only()
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        try:
            warnings = await self.get_warnings(interaction.guild_id, member.id)

            if not warnings:
                await interaction.followup.send(f"{member.name} has no warnings.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"⚠️ Warnings for {member.name}",
                color=discord.Color.yellow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )

            for moderator_id, reason, timestamp in warnings:
                # get_user uses cache; fetch_user is the API fallback for uncached users
                moderator = self.bot.get_user(moderator_id) or await self.bot.fetch_user(moderator_id)
                # SQLite returns timestamps as strings — convert to datetime for format_dt
                dt = datetime.datetime.fromisoformat(timestamp)
                embed.add_field(
                    name=f"**Warned by {moderator} on {discord.utils.format_dt(dt, style='d')}**",
                    value=reason,
                    inline=False
                )

            await interaction.followup.send(embed=embed)
            # No log here — viewing warnings is a read-only action, not a moderation action
        except Exception as e:
            await interaction.followup.send(f"An error occurred while fetching warnings: {str(e)}", ephemeral=True)

    @admin.command(name="clear_warnings", description="Clear all warnings for a member")
    @app_commands.describe(member="Member to clear warnings for")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guild_only()
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        try:
            await self.delete_warnings(interaction.guild_id, member.id)
            await interaction.followup.send(f"All warnings for {member.name} have been cleared.", ephemeral=True)

            # Log the warning clear
            log_embed = discord.Embed(
                title=f"🗑️ Warnings Cleared for {member.name}",
                color=discord.Color.yellow()
            )
            log_embed.set_thumbnail(url=member.display_avatar.url)
            log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_embed.add_field(name="Cleared At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
            await self.send_log(interaction.guild_id, log_embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred while clearing warnings: {str(e)}", ephemeral=True)

    @admin.command(name="purge", description="Bulk delete messages in a channel")
    @app_commands.describe(
        amount="Number of messages to delete (max 100)",
        user="Optionally specify a user to only delete their messages"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.User = None):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Please specify an amount between 1 and 100.", ephemeral=True)
            return

        # Send ephemeral response BEFORE purging — channel.purge() deletes all messages including
        # the deferred interaction message, which causes a 404 when trying to send a followup
        await interaction.response.send_message("Purging messages...", ephemeral=True)

        try:
            def check(m):
                return m.author == user if user else True

            deleted = await interaction.channel.purge(limit=amount, check=check)
            await interaction.edit_original_response(content=f"Deleted {len(deleted)} messages.")

            # Log the purge
            log_embed = discord.Embed(
                title=f"🧹 {len(deleted)} Messages Purged",
                description=f"**Channel:** {interaction.channel.mention}" + (f"\n**Target user:** {user.mention}" if user else ""),
                color=discord.Color.blurple()
            )
            log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_embed.add_field(name="Purged At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
            await self.send_log(interaction.guild_id, log_embed)
        except discord.Forbidden:
            await interaction.edit_original_response(content="I don't have permission to manage messages!")
        except Exception as e:
            await interaction.edit_original_response(content=f"An error occurred: {str(e)}")

    @admin.command(name="slowmode", description="Set slowmode delay for the channel")
    @app_commands.describe(delay="Slowmode delay in seconds (0 to disable)")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def slowmode(self, interaction: discord.Interaction, delay: int):
        # Discord's max slowmode is 6 hours (21600 seconds)
        if delay < 0 or delay > 21600:
            await interaction.response.send_message("Please specify a delay between 0 and 21600 seconds (6 hours).", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await interaction.channel.edit(slowmode_delay=delay, reason=f"Slowmode set by {interaction.user}")

            if delay == 0:
                await interaction.followup.send("Slowmode has been disabled for this channel.")
                log_desc = f"**Channel:** {interaction.channel.mention}\nSlowmode disabled."
            else:
                await interaction.followup.send(f"Slowmode has been set to {delay} seconds for this channel.")
                log_desc = f"**Channel:** {interaction.channel.mention}\n**Delay:** {delay} seconds"

            # Log the slowmode change
            log_embed = discord.Embed(
                title="🐢 Slowmode Updated",
                description=log_desc,
                color=discord.Color.blurple()
            )
            log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
            await self.send_log(interaction.guild_id, log_embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to manage channels!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @admin.command(name="lockdown", description="Toggle lockdown mode for the channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)

            # Toggle: if already locked (send_messages=False), lift it; otherwise lock it
            if overwrite.send_messages is False:
                overwrite.send_messages = None  # None = revert to default (inherit)
                await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Lockdown lifted by {interaction.user}")
                await interaction.followup.send("Lockdown has been lifted for this channel.")
                log_title = "🔓 Lockdown Lifted"
                log_color = discord.Color.green()
            else:
                overwrite.send_messages = False
                await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Lockdown enabled by {interaction.user}")
                await interaction.followup.send("Lockdown has been enabled for this channel. Only users with explicit permissions can send messages.")
                log_title = "🔒 Channel Locked Down"
                log_color = discord.Color.orange()

            # Log the lockdown toggle
            log_embed = discord.Embed(
                title=log_title,
                description=f"**Channel:** {interaction.channel.mention}",
                color=log_color
            )
            log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
            await self.send_log(interaction.guild_id, log_embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to manage channels!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @admin.command(name="unlockdown", description="Lift lockdown mode for the channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def unlockdown(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
            # Set to None to revert to default permissions (removes the explicit deny)
            overwrite.send_messages = None
            await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Lockdown lifted by {interaction.user}")
            await interaction.followup.send("Lockdown has been lifted for this channel.")

            # Log the unlockdown
            log_embed = discord.Embed(
                title="🔓 Lockdown Lifted",
                description=f"**Channel:** {interaction.channel.mention}",
                color=discord.Color.green()
            )
            log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style='d'), inline=True)
            await self.send_log(interaction.guild_id, log_embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to manage channels!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)


async def moderation_setup(bot):
    await bot.add_cog(ModerationCog(bot))
