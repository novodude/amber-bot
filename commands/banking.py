from os import name
import random
import discord
import aiosqlite
from discord import app_commands, channel
from datetime import datetime, timedelta
from utils.banking import ProfileView, build_profile_embed
from utils.userbase.ensure_registered import ensure_registered
from utils.economy import (
    add_dabloons, get_leaderboard, get_user_id_from_discord,
    get_dabloons, add_xp, get_level, get_xp
)


class Money(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="money",
            description="Manage your dabloons and economy commands"
        )

    @app_commands.command(name="daily", description="Claim your daily dabloons!")
    async def daily(self, interaction: discord.Interaction):
        # Auto-register if needed
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT daily_coin_claim FROM games WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            now = datetime.now()

            if row and row[0]:
                last_claim = datetime.fromisoformat(row[0])
                if now - last_claim < timedelta(hours=24):
                    remaining = timedelta(hours=24) - (now - last_claim)
                    await interaction.response.send_message(
                        f"You already claimed your daily coins! Try again in {str(remaining).split('.')[0]}.",
                        ephemeral=True
                    )
                    return

            daily_amount = random.randint(100, 200)
            await add_dabloons(user_id, daily_amount)
            xp = random.randint(40, 80)
            await add_xp(user_id, xp)
            await db.execute(
                "UPDATE games SET daily_coin_claim = ? WHERE user_id = ?",
                (now.isoformat(), user_id)
            )
            await db.commit()

        await interaction.response.send_message(f"You claimed {daily_amount} dabloons! 🪙\nYou also earned {xp} XP! Keep it up! 💪")

    @app_commands.command(name="give", description="Give dabloons to another user")
    @app_commands.describe(target="The user you want to give dabloons to", amount="Amount to give")
    async def give(self, interaction: discord.Interaction, target: discord.User, amount: int):
        # Auto-register sender; receiver must opt in themselves (fair play)
        sender_id = await ensure_registered(interaction.user.id, str(interaction.user))
        receiver_id = await get_user_id_from_discord(target.id)

        if receiver_id is None:
            await interaction.response.send_message(
                f"{target.mention} isn't registered yet — they need to use any economy command first!",
                ephemeral=True
            )
            return

        if amount <= 0:
            await interaction.response.send_message("You must send a positive amount!", ephemeral=True)
            return

        sender_balance = await get_dabloons(sender_id)
        if sender_balance < amount:
            await interaction.response.send_message("You don't have enough dabloons!", ephemeral=True)
            return

        await add_dabloons(sender_id, -amount)
        await add_dabloons(receiver_id, amount)

        await interaction.response.send_message(
            f"You sent {amount} dabloons to {target.mention}! 🪙"
        )

    @app_commands.command(name="balance", description="Check your current dabloons balance")
    async def balance(self, interaction: discord.Interaction):
        # Auto-register if needed
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)
        await interaction.response.send_message(f"You have 🪙 {balance} dabloons.")

    @app_commands.command(name="leaderboard", description="See the top 10 users by dabloon balance")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = await get_leaderboard()

        if not leaderboard:
            await interaction.response.send_message("No users found in the leaderboard.")
            return

        embed = discord.Embed(
            title="Dabloon Leaderboard",
            description="Top 10 users by dabloon balance",
            color=discord.Color.gold()
        )

        for rank, (username, dabloons) in enumerate(leaderboard, start=1):
            name = f"@{username}"
            embed.add_field(name=f"{rank}. {name}", value=f"🪙 {dabloons}", inline=False)

        await interaction.response.send_message(embed=embed)


async def banking_setup(bot):
    bot.tree.add_command(Money())

    @bot.tree.command(name="profile", description="Check your profile.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def profile(interaction: discord.Interaction):
        # Auto-register if needed
        discord_id = interaction.user.id
        user_id = await ensure_registered(discord_id, str(interaction.user))

        balance = await get_dabloons(user_id)

        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT bio, profile_color FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()

        bio = row[0] if row and row[0] else "This user has no bio set."
        color_name = row[1] if row and row[1] else "gold"

        current_hour = discord.utils.utcnow().hour
        greeting_time = (
            "morning" if 5 <= current_hour < 12 else
            "afternoon" if 12 <= current_hour < 17 else
            "evening" if 17 <= current_hour < 21 else
            "night"
        )

        embed = await build_profile_embed(
            discord_id=discord_id,
            user=interaction.user,
            balance=balance,
            bio=bio,
            color=ProfileView(discord_id).get_color(color_name),
            greeting_time=greeting_time,
        )

        view = ProfileView(discord_id)
        await interaction.response.send_message(embed=embed, view=view)

    @bot.tree.command(name="setbio", description="Set your custom bio")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def setbio(interaction: discord.Interaction, bio: str):
        # Auto-register if needed
        await ensure_registered(interaction.user.id, str(interaction.user))

        async with aiosqlite.connect("data/user.db") as db:
            await db.execute(
                "UPDATE users SET bio = ? WHERE discord_id = ?", (bio, interaction.user.id)
            )
            await db.commit()

        embed = discord.Embed(
            title="Bio Updated",
            description=f"Your bio has been set to:\n\n{bio}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="level", description="Check your current level and XP")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def level(interaction: discord.Interaction):
        # Auto-register if needed
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        level = await get_level(user_id)
        xp = await get_xp(user_id)
        xp_needed = int((100 * (level ** 1.2)) - xp)

        embed = discord.Embed(
            title=f"Level {level}",
            description=f"You have {xp} XP.\nYou need {xp_needed} more XP to reach the next level.",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def message_xp_handler(message):
    if message.author.bot:
        return

    user_id = await ensure_registered(message.author.id, str(message.author))
    new_level = await add_xp(user_id, None, message.content)
    if new_level:
        embed = discord.Embed(
            title="Level Up!",
            description=f"You've reached level {new_level}!\nquack on, {message.author.mention}!",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed, delete_after=10, reference=message)


