from typing import Literal
import random
import discord
import aiosqlite
import asyncio
from discord import app_commands
from datetime import datetime, timedelta
from utils.banking import ProfileView, build_profile_embed
from utils.userbase.ensure_registered import ensure_registered
from utils.economy import (
    add_dabloons, get_user_id_from_discord,
    get_dabloons, add_xp, get_level, get_xp,
    is_private_account
)


@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Money(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="money",
            description="Manage your dabloons and economy commands"
        )

    @app_commands.command(name="daily", description="Claim your daily dabloons!")
    async def daily(self, interaction: discord.Interaction):
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
            await add_xp(user_id, xp, None)
            await db.execute(
                "UPDATE games SET daily_coin_claim = ? WHERE user_id = ?",
                (now.isoformat(), user_id)
            )
            await db.commit()

        await interaction.response.send_message(f"You claimed {daily_amount} dabloons! 🪙\nYou also earned {xp} XP! Keep it up! 💪")

    @app_commands.command(name="give", description="Give dabloons to another user")
    @app_commands.describe(target="The user you want to give dabloons to", amount="Amount to give")
    async def give(self, interaction: discord.Interaction, target: discord.User, amount: int):
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
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)
        await interaction.response.send_message(f"You have 🪙 {balance} dabloons.")

    @app_commands.command(name="rob", description="Attempt to rob another user of their dabloons")
    @app_commands.describe(target="The user you want to rob")
    async def rob(self, interaction: discord.Interaction, target: discord.User):
        robber_id = await ensure_registered(interaction.user.id, str(interaction.user))
        victim_id = await get_user_id_from_discord(target.id)

        if victim_id is None:
            await interaction.response.send_message(
                f"{target.mention} isn't registered yet",
                ephemeral=True
            )
            return

        if victim_id == robber_id:
            embed = discord.Embed(
                title="Nice Try!",
                description="You can't rob yourself! That's just sad. 🪙",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        victim_balance = await get_dabloons(victim_id)
        if victim_balance < 50:
            embed = discord.Embed(
                title="Too Poor to Rob",
                description=f"{target.mention} doesn't have enough dabloons to rob! They need at least 50 dabloons. 🪙",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        success_chance = 0.5
        if random.random() < success_chance:
            stolen_amount = random.randint(10, min(50, victim_balance))
            await add_dabloons(victim_id, -stolen_amount)
            await add_dabloons(robber_id, stolen_amount)
            embed = discord.Embed(
                title="Robbery Successful!",
                description=f"You successfully robbed {target.mention} and stole {stolen_amount} dabloons! 🪙",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            penalty_amount = random.randint(10, 30)
            await add_dabloons(robber_id, -penalty_amount)
            await add_dabloons(victim_id, penalty_amount)
            embed = discord.Embed(
                title="Robbery Failed!",
                description=f"You got caught trying to rob {target.mention} and lost {penalty_amount} dabloons in the escape! 🪙",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beg", description="Beg for dabloons from other users")
    async def beg(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        big_chance = 0.1
        medium_chance = 0.3
        small_chance = 0.5
        if random.random() < big_chance:
            amount = random.randint(50, 200)
            title = "Generous Soul!"
            description = f"Wow, someone felt really generous and gave you {amount} dabloons! 🪙"
            color = discord.Color.gold()
            await add_dabloons(user_id, amount)
        elif random.random() < medium_chance:
            amount = random.randint(20, 50)
            title = "Lucky Break!"
            description = f"Someone felt generous and gave you {amount} dabloons! 🪙"
            color = discord.Color.green()
            await add_dabloons(user_id, amount)
        elif random.random() < small_chance:
            amount = random.randint(5, 20)
            title = "Small Blessing"
            description = f"Someone felt a little generous and gave you {amount} dabloons! 🪙"
            color = discord.Color.blue()
            await add_dabloons(user_id, amount)
        else:
            title = "Tough Crowd"
            description = "No one felt like giving you dabloons this time. Better luck next time! 🪙"
            color = discord.Color.red()

        embed = discord.Embed(title=title, description=description, color=color)
        await interaction.response.send_message(embed=embed)

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Gamble(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="gamble",
            description="Try your luck with some gambling games!"
        )

    SLOT_EMOJI = ["🍒", "🍋", "🍊", "🍇", "⭐", "7️⃣"]

    @app_commands.command(name="coinflip", description="Flip a coin and bet on heads or tails")
    @app_commands.describe(bet="The amount of dabloons you want to bet", choice="Your choice: heads or tails")
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: Literal["heads", "tails"]):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)

        if bet <= 0:
            await interaction.response.send_message("You must bet a positive amount!", ephemeral=True)
            return

        if bet > balance:
            await interaction.response.send_message("You don't have enough dabloons to make that bet!", ephemeral=True)
            return

        result = random.choice(["heads", "tails"])
        if choice == result:
            winnings = bet
            await add_dabloons(user_id, winnings)
            embed = discord.Embed(
                title="You Win!",
                description=f"The coin landed on {result}! You won {winnings} dabloons! 🪙",
                color=discord.Color.green()
            )
        else:
            await add_dabloons(user_id, -bet)
            embed = discord.Embed(
                title="You Lose!",
                description=f"The coin landed on {result}. You lost {bet} dabloons! 🪙",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="Roll a 6-sided die and bet on the outcome")
    @app_commands.describe(bet="The amount of dabloons you want to bet", choice="Your choice: a number from 1 to 6")
    async def roll(self, interaction: discord.Interaction, bet: int, choice: Literal[1, 2, 3, 4, 5, 6]):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)

        if bet <= 0:
            await interaction.response.send_message("You must bet a positive amount!", ephemeral=True)
            return

        if bet > balance:
            await interaction.response.send_message("You don't have enough dabloons to make that bet!", ephemeral=True)
            return

        result = random.randint(1, 6)
        if choice == result:
            winnings = bet * 5
            await add_dabloons(user_id, winnings)
            embed = discord.Embed(
                title="You Win!",
                description=f"You rolled a {result}! You won {winnings} dabloons! 🪙",
                color=discord.Color.green()
            )
        else:
            await add_dabloons(user_id, -bet)
            embed = discord.Embed(
                title="You Lose!",
                description=f"You rolled a {result}. You lost {bet} dabloons! 🪙",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Spin the slot machine and bet on the outcome")
    @app_commands.describe(bet="The amount of dabloons you want to bet")
    async def slots(self, interaction: discord.Interaction, bet: int):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)

        if bet <= 0:
            await interaction.response.send_message("You must bet a positive amount!", ephemeral=True)
            return

        if bet > balance:
            await interaction.response.send_message("You don't have enough dabloons to make that bet!", ephemeral=True)
            return

        embed = discord.Embed(title="Spinning...", description="🎰", color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

        for _ in range(3):
            slot_result = [random.choice(self.SLOT_EMOJI) for _ in range(3)]
            embed = discord.Embed(
                title="Spinning...",
                description=f"{' | '.join(slot_result)}",
                color=discord.Color.yellow()
            )
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(0.7)

        result = [random.choice(self.SLOT_EMOJI) for _ in range(3)]
        embed = discord.Embed(
            title="Final Result",
            description=f"{' | '.join(result)}",
            color=discord.Color.yellow()
        )
        await asyncio.sleep(0.7)

        if len(set(result)) == 1:
            winnings = bet * 10
            await add_dabloons(user_id, winnings)
            embed.title = "Jackpot!"
            embed.description += f"\nYou won {winnings} dabloons! 🪙"
            embed.color = discord.Color.green()
        elif len(set(result)) == 2:
            winnings = bet * 2
            await add_dabloons(user_id, winnings)
            embed.title = "Small Win!"
            embed.description += f"\nYou won {winnings} dabloons! 🪙"
            embed.color = discord.Color.blue()
        else:
            await add_dabloons(user_id, -bet)
            embed.title = "You Lose!"
            embed.description += f"\nYou lost {bet} dabloons! 🪙"
            embed.color = discord.Color.red()
        await interaction.edit_original_response(embed=embed)


async def banking_setup(bot):
    bot.tree.add_command(Money())
    bot.tree.add_command(Gamble())

    @bot.tree.command(name="profile", description="Check your profile.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def profile(interaction: discord.Interaction, user: discord.User = None):
        discord_id  = interaction.user.id if user is None else user.id
        target_user = interaction.user    if user is None else user

        if user is None:
            user_id = await ensure_registered(discord_id, str(interaction.user))
        else:
            user_id = await get_user_id_from_discord(discord_id)
            if user_id is None:
                await interaction.response.send_message(
                    f"{user.mention} isn't registered yet",
                    ephemeral=True
                )
                return

        if await is_private_account(discord_id):
            await interaction.response.send_message(
                f"{user.mention} isn't registered yet",
                ephemeral=True
            )
            return

        balance = await get_dabloons(user_id)
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT bio, profile_color, custom_hex_color FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()

        bio        = row[0] if row and row[0] else "This user has no bio set."
        color_name = row[1] if row and row[1] else "gold"
        custom_hex = row[2] if row and row[2] else None

        current_hour = discord.utils.utcnow().hour
        greeting_time = (
            "morning"   if 5  <= current_hour < 12 else
            "afternoon" if 12 <= current_hour < 17 else
            "evening"   if 17 <= current_hour < 21 else
            "night"
        )

        view = ProfileView(discord_id) if user is None else None
        resolved_color = view.get_color(color_name, custom_hex) if view else ProfileView(discord_id).get_color(color_name, custom_hex)

        embed = await build_profile_embed(
            discord_id=discord_id,
            user=target_user,
            balance=balance,
            bio=bio,
            color=resolved_color,
            greeting_time=greeting_time,
        )

        await interaction.response.send_message(embed=embed, view=view)

    @bot.tree.command(name="setbio", description="Set your custom bio")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def setbio(interaction: discord.Interaction, bio: str):
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
