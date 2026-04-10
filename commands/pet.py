"""commands/pet.py — pet system cog"""
import discord
import random
import aiosqlite
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands, tasks

from utils.userbase.database import DB_PATH
from utils.userbase.ensure_registered import ensure_registered
from utils.pet import (
    get_pet, create_pet, update_pet, add_pet_xp, feed_pet,
    equip_accessory, touch_owner_activity,
    get_unlocked_slots, get_hat_emoji, get_toy_style,
    xp_to_next_level, apply_decay, SLOT_LABELS,
)
from utils.cat_model import build_check_in_message


# ── Inactivity threshold before the cat checks in ─────────────────────────────
INACTIVITY_HOURS = 4   # owner must be quiet for 4h before cat messages
MIN_MSG_INTERVAL = 6   # cat won't message the same owner twice within 6h


def hunger_bar(value: int) -> str:
    filled = round(value / 10)
    return "█" * filled + "░" * (10 - filled) + f" {value}%"

def happy_bar(value: int) -> str:
    filled = round(value / 10)
    return "🟡" * filled + "⬜" * (10 - filled) + f" {value}%"


class PetCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_in_loop.start()

    def cog_unload(self):
        self.check_in_loop.cancel()

    # ── Background task ────────────────────────────────────────────────────────
    @tasks.loop(minutes=30)
    async def check_in_loop(self):
        """Every 30 min, scan for pets whose owners have been inactive long enough."""
        now = datetime.utcnow()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT p.*, u.discord_id
                FROM pets p
                JOIN users u ON u.id = p.user_id
                WHERE p.last_owner_activity IS NOT NULL
            """)
            rows = await cursor.fetchall()

        for row in rows:
            pet = dict(row)
            discord_id = pet["discord_id"]

            # Check inactivity window
            last_active = datetime.fromisoformat(pet["last_owner_activity"]) if pet["last_owner_activity"] else now
            if (now - last_active).total_seconds() < INACTIVITY_HOURS * 3600:
                continue

            # Check that we haven't messaged recently
            last_msg = datetime.fromisoformat(pet["last_message_sent"]) if pet["last_message_sent"] else datetime.min
            if (now - last_msg).total_seconds() < MIN_MSG_INTERVAL * 3600:
                continue

            try:
                user = await self.bot.fetch_user(discord_id)
            except Exception:
                continue

            # Compute current state with decay
            last_fed    = datetime.fromisoformat(pet["last_fed"])    if pet["last_fed"]    else now
            last_played = datetime.fromisoformat(pet["last_played"]) if pet["last_played"] else now
            hunger, happiness = apply_decay(pet["hunger"], pet["happiness"], last_fed, last_played)

            toy_style = get_toy_style(pet.get("slot_toy"))
            message   = build_check_in_message(
                pet_name=pet["name"],
                happiness=happiness,
                hunger=hunger,
                toy_style=toy_style,
            )

            # Send via DM (no per-guild user mapping exists in the DB to pick
            # a specific guild channel, so DM is the only safe delivery path)
            try:
                await user.send(message)
                await update_pet(pet["user_id"], last_message_sent=now.isoformat())
            except Exception:
                pass

    @check_in_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ── /pet adopt ────────────────────────────────────────────────────────────
    pet_group = app_commands.Group(name="pet", description="Your cat companion")

    @pet_group.command(name="adopt", description="Adopt your cat companion and give it a name")
    @app_commands.describe(name="What will you name your cat?")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def adopt(self, interaction: discord.Interaction, name: str):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        existing = await get_pet(user_id)
        if existing:
            await interaction.response.send_message(
                f"You already have a cat named **{existing['name']}**! Use `/pet status` to check on them.",
                ephemeral=True
            )
            return

        if len(name) > 32:
            await interaction.response.send_message("Name must be 32 characters or less!", ephemeral=True)
            return

        await create_pet(user_id, name)
        embed = discord.Embed(
            title="🐱 A new cat has arrived!",
            description=(
                f"**{name}** has chosen you as their owner!\n\n"
                "They start with full hunger and happiness.\n"
                "Feed them with `/pet feed`, play with `/pet play`, and check in with `/pet status`.\n\n"
                "Your cat will message you when you've been away for a while 🐾"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="quack... i mean meow")
        await interaction.response.send_message(embed=embed)

    # ── /pet status ────────────────────────────────────────────────────────────
    @pet_group.command(name="status", description="Check on your cat")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def status(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        pet = await get_pet(user_id)
        if not pet:
            await interaction.response.send_message(
                "You don't have a cat yet! Use `/pet adopt` to get one.", ephemeral=True
            )
            return

        last_fed    = datetime.fromisoformat(pet["last_fed"])    if pet["last_fed"]    else datetime.utcnow()
        last_played = datetime.fromisoformat(pet["last_played"]) if pet["last_played"] else datetime.utcnow()
        hunger, happiness = apply_decay(pet["hunger"], pet["happiness"], last_fed, last_played)

        hat_emoji  = get_hat_emoji(pet.get("slot_hat"))
        toy_style  = get_toy_style(pet.get("slot_toy"))
        unlocked   = get_unlocked_slots(pet["level"])
        xp_needed  = xp_to_next_level(pet["level"])

        # Mood line based on state
        if hunger < 20:
            mood = "😿 Starving... please feed me"
        elif happiness < 30:
            mood = "😾 Very unhappy..."
        elif toy_style == "zoomies":
            mood = "😻 ZOOMIES TIME"
        elif happiness > 80:
            mood = "😺 Purring contentedly"
        else:
            mood = "🐱 Doing okay"

        embed = discord.Embed(
            title=f"{hat_emoji} {pet['name']} — Level {pet['level']} Cat",
            description=mood,
            color=discord.Color.orange()
        )
        embed.add_field(name="🍖 Hunger",    value=hunger_bar(hunger),    inline=False)
        embed.add_field(name="😊 Happiness", value=happy_bar(happiness),  inline=False)
        embed.add_field(
            name="✨ Experience",
            value=f"{pet['experience']} / {xp_needed} XP",
            inline=True
        )
        embed.add_field(name="⬆️ Level", value=str(pet["level"]), inline=True)

        # Accessory slots
        slot_lines = []
        for slot in ["slot_collar", "slot_bow", "slot_hat", "slot_toy", "slot_extra1", "slot_extra2"]:
            label   = SLOT_LABELS[slot]
            equipped = pet.get(slot)
            if slot in unlocked:
                slot_lines.append(f"**{label}:** {equipped or '*(empty)*'}")
            else:
                level_req = next(lv for lv, slots in {5:["slot_extra1"],10:["slot_extra2"]}.items() if slot in slots) if slot in ["slot_extra1","slot_extra2"] else None
                if level_req:
                    slot_lines.append(f"**{label}:** 🔒 Unlocks at level {level_req}")

        if slot_lines:
            embed.add_field(name="🎀 Accessories", value="\n".join(slot_lines), inline=False)

        embed.set_footer(text="Use /pet feed, /pet play, /pet equip to interact!")
        await interaction.response.send_message(embed=embed)
        # Update activity
        await touch_owner_activity(user_id)

    # ── /pet feed ─────────────────────────────────────────────────────────────
    @pet_group.command(name="feed", description="Feed your cat using food from your inventory")
    @app_commands.describe(item="Food item to use")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def feed(self, interaction: discord.Interaction, item: str):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        pet = await get_pet(user_id)
        if not pet:
            await interaction.response.send_message("You don't have a cat yet!", ephemeral=True)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            # Check inventory
            cursor = await db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item)
            )
            row = await cursor.fetchone()
            if not row or row[0] < 1:
                await interaction.response.send_message(
                    f"You don't have any **{item}** in your inventory! Buy some from `/shop`.",
                    ephemeral=True
                )
                return

            # Get item effect
            cursor = await db.execute(
                "SELECT effect, category FROM shop WHERE item_name = ?", (item,)
            )
            shop_row = await cursor.fetchone()
            if not shop_row or shop_row[1] != "pet_food":
                await interaction.response.send_message(
                    f"**{item}** isn't pet food!", ephemeral=True
                )
                return

            effect = shop_row[0]

            # Deduct from inventory
            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?",
                (user_id, item)
            )
            await db.commit()

        new_hunger, new_happiness = await feed_pet(user_id, effect)
        await touch_owner_activity(user_id)

        embed = discord.Embed(
            title=f"🍽️ {pet['name']} ate {item}!",
            color=discord.Color.green()
        )
        embed.add_field(name="🍖 Hunger",    value=hunger_bar(new_hunger),    inline=False)
        embed.add_field(name="😊 Happiness", value=happy_bar(new_happiness),  inline=False)
        await interaction.response.send_message(embed=embed)

    # ── /pet play ─────────────────────────────────────────────────────────────
    @pet_group.command(name="play", description="Play with your cat to boost their happiness")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def play(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        pet = await get_pet(user_id)
        if not pet:
            await interaction.response.send_message("You don't have a cat yet!", ephemeral=True)
            return

        last_played = datetime.fromisoformat(pet["last_played"]) if pet["last_played"] else datetime.min
        cooldown    = timedelta(hours=1)
        if datetime.utcnow() - last_played < cooldown:
            remaining = cooldown - (datetime.utcnow() - last_played)
            mins = int(remaining.total_seconds() / 60)
            await interaction.response.send_message(
                f"{pet['name']} is tired! Play again in **{mins} minutes**.", ephemeral=True
            )
            return

        happiness_gain = random.randint(10, 25)
        xp_gain        = random.randint(10, 20)

        last_fed_dt = datetime.fromisoformat(pet["last_fed"]) if pet["last_fed"] else datetime.utcnow()
        hunger, happiness = apply_decay(
            pet["hunger"], pet["happiness"], last_fed_dt, last_played
        )
        new_happiness = min(100, happiness + happiness_gain)

        await update_pet(
            user_id,
            happiness=new_happiness,
            hunger=hunger,
            last_played=datetime.utcnow().isoformat()
        )
        levelled = await add_pet_xp(user_id, xp_gain)
        await touch_owner_activity(user_id)

        toy_style = get_toy_style(pet.get("slot_toy"))
        cat_says = build_check_in_message(
            pet["name"], new_happiness, hunger, toy_style,
            owner_context="want to play?"
        )

        embed = discord.Embed(
            title=f"🎮 Playing with {pet['name']}!",
            description=cat_says,
            color=discord.Color.purple()
        )
        embed.add_field(name="😊 Happiness", value=happy_bar(new_happiness), inline=False)
        embed.add_field(name="✨ XP gained", value=f"+{xp_gain} XP", inline=True)

        if levelled:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"{pet['name']} is now **Level {levelled}**!",
                inline=False
            )
            unlocked = get_unlocked_slots(levelled)
            new_slots = [SLOT_LABELS[s] for s in unlocked if s in ["slot_extra1", "slot_extra2"] and levelled in [5, 10]]
            if new_slots:
                embed.add_field(
                    name="🔓 New slot unlocked!",
                    value=", ".join(new_slots),
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    # ── /pet rename ───────────────────────────────────────────────────────────
    @pet_group.command(name="rename", description="Give your cat a new name")
    @app_commands.describe(name="New name for your cat")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rename(self, interaction: discord.Interaction, name: str):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        pet = await get_pet(user_id)
        if not pet:
            await interaction.response.send_message("You don't have a cat yet!", ephemeral=True)
            return
        if len(name) > 32:
            await interaction.response.send_message("Name must be 32 characters or less!", ephemeral=True)
            return

        old_name = pet["name"]
        await update_pet(user_id, name=name)
        await interaction.response.send_message(
            f"**{old_name}** has been renamed to **{name}**! 🐱", ephemeral=True
        )

    # ── /pet equip ────────────────────────────────────────────────────────────
    @pet_group.command(name="equip", description="Equip an accessory to your cat")
    @app_commands.describe(slot="Which slot to equip", item="Item name (must be in your inventory)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def equip(self, interaction: discord.Interaction, slot: str, item: str):
        SLOT_MAP = {
            "collar": "slot_collar",
            "bow":    "slot_bow",
            "hat":    "slot_hat",
            "toy":    "slot_toy",
            "extra1": "slot_extra1",
            "extra2": "slot_extra2",
        }
        slot_key = SLOT_MAP.get(slot.lower())
        if not slot_key:
            await interaction.response.send_message(
                f"Unknown slot `{slot}`. Valid slots: {', '.join(SLOT_MAP.keys())}", ephemeral=True
            )
            return

        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        # Check inventory
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item)
            )
            row = await cursor.fetchone()
            if not row or row[0] < 1:
                await interaction.response.send_message(
                    f"You don't have **{item}** in your inventory!", ephemeral=True
                )
                return

        ok = await equip_accessory(user_id, slot_key, item)
        if not ok:
            await interaction.response.send_message(
                "That slot is locked! Level up your pet to unlock more slots.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Equipped **{item}** to your cat's **{slot}** slot! 🎀"
        )

    # ── /pet unequip ──────────────────────────────────────────────────────────
    @pet_group.command(name="unequip", description="Remove an accessory from a slot")
    @app_commands.describe(slot="Which slot to clear")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def unequip(self, interaction: discord.Interaction, slot: str):
        SLOT_MAP = {
            "collar": "slot_collar", "bow": "slot_bow",
            "hat": "slot_hat", "toy": "slot_toy",
            "extra1": "slot_extra1", "extra2": "slot_extra2",
        }
        slot_key = SLOT_MAP.get(slot.lower())
        if not slot_key:
            await interaction.response.send_message(
                f"Unknown slot `{slot}`.", ephemeral=True
            )
            return

        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        await equip_accessory(user_id, slot_key, None)
        await interaction.response.send_message(
            f"Removed item from **{slot}** slot.", ephemeral=True
        )

    # ── /pet candy ────────────────────────────────────────────────────────────
    @pet_group.command(name="candy", description="Use candy to give your pet XP")
    @app_commands.describe(item="Candy item to use (XP Candy / Rare Candy / Mega Candy)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def candy(self, interaction: discord.Interaction, item: str):
        CANDY_MAP = {
            "XP Candy":   50,
            "Rare Candy": 200,
            "Mega Candy": 500,
        }
        if item not in CANDY_MAP:
            await interaction.response.send_message(
                f"Unknown candy `{item}`. Valid: {', '.join(CANDY_MAP.keys())}", ephemeral=True
            )
            return

        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        pet = await get_pet(user_id)
        if not pet:
            await interaction.response.send_message("You don't have a cat yet!", ephemeral=True)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item)
            )
            row = await cursor.fetchone()
            if not row or row[0] < 1:
                await interaction.response.send_message(
                    f"You don't have any **{item}**! Buy some from `/shop`.", ephemeral=True
                )
                return
            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?",
                (user_id, item)
            )
            await db.commit()

        xp_gain  = CANDY_MAP[item]
        levelled = await add_pet_xp(user_id, xp_gain)

        embed = discord.Embed(
            title=f"🍬 {pet['name']} ate {item}!",
            description=f"+**{xp_gain} XP** gained!",
            color=discord.Color.pink()
        )
        if levelled:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"{pet['name']} is now **Level {levelled}**!",
                inline=False
            )
        await interaction.response.send_message(embed=embed)


async def pet_setup(bot: commands.Bot):
    await bot.add_cog(PetCog(bot))
