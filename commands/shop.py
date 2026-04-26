"""commands/shop.py — full shop system"""
import discord
import aiosqlite
import re
from discord import app_commands
from discord.ext import commands

from utils.userbase.database import DB_PATH
from utils.userbase.ensure_registered import ensure_registered
from utils.economy import get_dabloons

CATEGORY_LABELS = {
    "games":        "🎮 Games",
    "pet_food":     "🍖 Pet Food",
    "accessory":    "🎀 Accessories",
    "candy":        "🍬 Pet Candy",
    "profile_color":"🎨 Profile Colors",
}


async def get_shop_items(category: str | None = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category:
            cursor = await db.execute(
                "SELECT * FROM shop WHERE category = ? ORDER BY price ASC", (category,)
            )
        else:
            cursor = await db.execute("SELECT * FROM shop ORDER BY category, price ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_inventory(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_name",
            (user_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def has_purchase(user_id: int, item_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM user_purchases WHERE user_id = ? AND item_name = ? AND active = 1",
            (user_id, item_name)
        )
        return await cursor.fetchone() is not None


async def add_to_inventory(user_id: int, item_name: str, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_name, qty, qty))
        await db.commit()


async def add_purchase(user_id: int, item_name: str, custom_value: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_purchases (user_id, item_name, custom_value) VALUES (?, ?, ?)",
            (user_id, item_name, custom_value)
        )
        await db.commit()


def build_shop_embed(items: list[dict], category_label: str, balance: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"🛒 Shop — {category_label}",
        description=f"Your balance: **🪙 {balance} dabloons**",
        color=discord.Color.gold()
    )
    for item in items:
        embed.add_field(
            name=f"{item['emoji']} {item['item_name']} — 🪙 {item['price']}",
            value=item["description"],
            inline=False
        )
    embed.set_footer(text="Use /shop buy <item> to purchase • /shop inventory to see what you own")
    return embed


class CategorySelect(discord.ui.Select):
    def __init__(self, balance: int):
        self.balance = balance
        options = [
            discord.SelectOption(label=label, value=cat, emoji=label.split()[0])
            for cat, label in CATEGORY_LABELS.items()
        ]
        super().__init__(placeholder="📂 Browse a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        items = await get_shop_items(self.values[0])
        label = CATEGORY_LABELS[self.values[0]]
        embed = build_shop_embed(items, label, self.balance)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ShopView(discord.ui.View):
    def __init__(self, balance: int):
        super().__init__(timeout=180)
        self.add_item(CategorySelect(balance))


class HexColorModal(discord.ui.Modal, title="Enter your hex color"):
    hex_input = discord.ui.TextInput(
        label="Hex color (e.g. #FF5733)",
        placeholder="#FF5733",
        min_length=7,
        max_length=7,
    )

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        value = self.hex_input.value.strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            await interaction.response.send_message(
                "Invalid hex color. Use the format `#RRGGBB`.", ephemeral=True
            )
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET custom_hex_color = ?, profile_color = 'custom' WHERE id = ?",
                (value, self.user_id)
            )
            await db.commit()

        r, g, b = int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
        preview_color = discord.Color.from_rgb(r, g, b)

        embed = discord.Embed(
            title="🎨 Custom color applied!",
            description=f"Your profile color is now `{value}`",
            color=preview_color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    shop_group = app_commands.Group(name="shop", description="Browse and buy items")

    # ── /shop browse ──────────────────────────────────────────────────────────
    @shop_group.command(name="browse", description="Browse the shop")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def browse(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        balance = await get_dabloons(user_id)

        items   = await get_shop_items("games")
        embed   = build_shop_embed(items, CATEGORY_LABELS["games"], balance)
        view    = ShopView(balance)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── /shop buy ─────────────────────────────────────────────────────────────
    @shop_group.command(name="buy", description="Purchase an item from the shop")
    @app_commands.describe(item="Name of the item to buy")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def buy(self, interaction: discord.Interaction, item: str):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM shop WHERE LOWER(item_name) = LOWER(?)", (item,)
            )
            row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(
                f"Item **{item}** not found. Check `/shop browse` for available items.", ephemeral=True
            )
            return

        shop_item = dict(row)
        balance   = await get_dabloons(user_id)

        if balance < shop_item["price"]:
            await interaction.response.send_message(
                f"You need **{shop_item['price']} 🪙** but only have **{balance} 🪙**.", ephemeral=True
            )
            return

        category = shop_item["category"]
        effect   = shop_item["effect"]

        # ── One-time unlocks (games, profile colors) ──────────────────────────
        if category in ("games", "profile_color") and effect != "color_custom":
            if await has_purchase(user_id, shop_item["item_name"]):
                await interaction.response.send_message(
                    f"You already own **{shop_item['item_name']}**!", ephemeral=True
                )
                return

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET amber_dabloons = amber_dabloons - ? WHERE id = ?",
                    (shop_item["price"], user_id)
                )
                await db.execute(
                    "INSERT INTO user_purchases (user_id, item_name, custom_value) VALUES (?, ?, ?)",
                    (user_id, shop_item["item_name"], None)
                )
                await db.commit()

            if effect.startswith("color_") and effect != "color_custom":
                color_name = effect[len("color_"):]
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET profile_color = ? WHERE id = ?",
                        (color_name, user_id)
                    )
                    await db.commit()

            embed = discord.Embed(
                title=f"✅ Purchased {shop_item['emoji']} {shop_item['item_name']}!",
                description=shop_item["description"],
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Remaining balance: 🪙 {balance - shop_item['price']}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ── Custom hex color ──────────────────────────────────────────────────
        if effect == "color_custom":
            if not await has_purchase(user_id, shop_item["item_name"]):
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET amber_dabloons = amber_dabloons - ? WHERE id = ?",
                        (shop_item["price"], user_id)
                    )
                    await db.execute(
                        "INSERT INTO user_purchases (user_id, item_name, custom_value) VALUES (?, ?, ?)",
                        (user_id, shop_item["item_name"], None)
                    )
                    await db.commit()
            await interaction.response.send_modal(HexColorModal(user_id))
            return

        # ── Consumables and accessories → inventory ───────────────────────────
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET amber_dabloons = amber_dabloons - ? WHERE id = ?",
                (shop_item["price"], user_id)
            )
            await db.commit()

        await add_to_inventory(user_id, shop_item["item_name"], 1)

        embed = discord.Embed(
            title=f"✅ Purchased {shop_item['emoji']} {shop_item['item_name']}!",
            description=f"{shop_item['description']}\n\nAdded to your inventory.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Remaining balance: 🪙 {balance - shop_item['price']}")

        if category == "accessory":
            embed.add_field(
                name="How to use",
                value="Use `/pet equip <slot> <item>` to equip it to your cat!",
                inline=False
            )
        elif category in ("pet_food", "candy"):
            embed.add_field(
                name="How to use",
                value="Use `/pet feed <item>` or `/pet candy <item>`.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /shop inventory ───────────────────────────────────────────────────────
    @shop_group.command(name="inventory", description="View your inventory")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def inventory(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        items   = await get_inventory(user_id)

        if not items:
            await interaction.response.send_message(
                "Your inventory is empty! Visit `/shop browse` to buy something.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎒 Your Inventory",
            color=discord.Color.blurple()
        )
        for item in items:
            embed.add_field(
                name=item["item_name"],
                value=f"x{item['quantity']}",
                inline=True
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /shop mypurchases ─────────────────────────────────────────────────────
    @shop_group.command(name="mypurchases", description="View your permanent unlocks")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def mypurchases(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT item_name, purchased_at FROM user_purchases WHERE user_id = ? AND active = 1 ORDER BY purchased_at DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()

        if not rows:
            await interaction.response.send_message(
                "No permanent unlocks yet! Check `/shop browse`.", ephemeral=True
            )
            return

        embed = discord.Embed(title="🔓 Your Unlocks", color=discord.Color.gold())
        for item_name, purchased_at in rows:
            date_str = purchased_at[:10] if purchased_at else "Unknown"
            embed.add_field(name=item_name, value=f"Bought: {date_str}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def shop_setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))
