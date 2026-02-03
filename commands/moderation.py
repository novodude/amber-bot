from os import name
import discord
from discord.ext import commands
from discord import Embed, app_commands, utils


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Error handler for ALL commands in this cog
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        command_name = interaction.command.name if interaction.command else "unknown"
        if isinstance(error, app_commands.MissingPermissions):
            message = f"You don't have permission to use this command"
        else:
            message = f"An error occurred: {str(error)}"
        
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except:
            await interaction.followup.send(message, ephemeral=True)
    
    # Helper function to check if bot can moderate a member
    async def can_moderate_member(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        """Returns True if the bot can moderate the member, False otherwise (and sends error message)"""
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I cannot moderate this member because their role is higher than or equal to mine!",
                ephemeral=True
            )
            return False
        
        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "I cannot moderate the server owner!",
                ephemeral=True
            )
            return False
        
        return True
    
    # Helper function to create moderation embed with time in server
    def create_mod_embed(self, member: discord.Member, interaction: discord.Interaction, 
                         title: str, reason: str = None, color: discord.Color = discord.Color.red()) -> discord.Embed:
        """Creates a standardized moderation embed"""
        today = discord.utils.utcnow()
        time_in_server = today - member.joined_at
        days = time_in_server.days
        
        embed = discord.Embed(
            title=title,
            description=f"They were in the server for {days} days\n**reason**:\n{reason}",
            color=color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        
        embed.add_field(
            name="Joined Server",
            value=discord.utils.format_dt(member.joined_at, style='R'),
            inline=True
        )
        embed.add_field(
            name="Left Server",
            value=discord.utils.format_dt(today, style='d'),
            inline=True
        )
        
        return embed
    
    admin = app_commands.Group(name="admin", description="collection of admin commands")
    
    @admin.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick")
    @app_commands.describe(reason="give reason for the kick")
    @app_commands.checks.has_permissions(administrator=True, kick_members=True)
    @app_commands.guild_only()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not await self.can_moderate_member(interaction, member):
            return
        
        await interaction.response.defer()
        
        embed = self.create_mod_embed(
            member=member,
            interaction=interaction,
            title=f"see you later {member.name}",
            reason=reason,
            color=discord.Color.red()
        )
        
        await member.kick(reason=f"Kicked by {interaction.user}")
        await interaction.followup.send(embed=embed)
    
    @admin.command(name="ban", description="Ban a member")
    @app_commands.describe(member="Member to ban")
    @app_commands.describe(reason="give reason for the ban")
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
                title=f"see you later {member.name}",
                reason=reason,
                color=discord.Color.red()
            )
            
            await member.ban(reason=f"{reason} | Banned by {interaction.user}")
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to ban members! Please check my role permissions.",
                ephemeral=True
            )
    
    @admin.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The ID of the user to unban")
    @app_commands.describe(reason="give reason for the unban")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        # Validate the user ID
        try:
            user_id_int = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Invalid user ID!",
                description="Please provide a valid numerical ID.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Fetch the banned user
            banned_user = await self.bot.fetch_user(user_id_int)
            
            # Try to unban
            await interaction.guild.unban(banned_user, reason=f"Unbanned by {interaction.user}")
            
            embed = discord.Embed(
                title=f"welcome back {banned_user.name}",
                description=f"**reason**:\n{reason}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=banned_user.display_avatar.url)
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.NotFound:
            await interaction.followup.send(
                "This user is not banned or doesn't exist!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to unban members! Please check my role permissions.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

async def moderation_setup(bot):
    await bot.add_cog(ModerationCog(bot))
