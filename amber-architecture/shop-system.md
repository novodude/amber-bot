# Shop System

The item shop where players spend dabloons on upgrades, pet supplies, and cosmetics.

---

## Overview

The shop is backed by the `shop` table in `user.db`, seeded on every `init_user_db()` call with `INSERT OR IGNORE`. Items are categorized and have machine-readable effect codes.

Players buy items through `/shop buy [item]`. Depending on the category, the item either goes into the `inventory` table (consumables/accessories) or into `user_purchases` (permanent one-time unlocks).

---

## Categories

### 🎮 Games (`category = 'games'`)

One-time purchases stored in `user_purchases`. Checked by game commands to modify behavior.

| Item | Price | Effect |
|---|---|---|
| Auto Clicker | 500 | Automatically clicks in Duck Clicker every 60s |
| Double Points | 750 | Duck Clicker awards 4 dabloons per 5 clicks instead of 2 |
| Custom X Symbol | 300 | Replaces ❌ with ⭐ in Tic Tac Toe |
| Custom O Symbol | 300 | Replaces ⭕ with 💫 in Tic Tac Toe |

### 🍖 Pet Food (`category = 'pet_food'`)

Consumables stored in `inventory`. Used via `/pet feed [item]`. Quantity is decremented on each use.

| Item | Price | Effect string | What it does |
|---|---|---|---|
| Kibble | 30 | `hunger_20` | +20 hunger |
| Tuna Can | 80 | `hunger_50` | +50 hunger |
| Fancy Feast | 150 | `hunger_100_hap_10` | +100 hunger, +10 happiness |
| Treat Bag | 50 | `happiness_15` | +15 happiness |

### 🎀 Accessories (`category = 'accessory'`)

Consumables stored in `inventory`. Equipped via `/pet equip [slot] [item]`. Not consumed on equip — can be swapped between slots freely.

| Item | Price | Slot |
|---|---|---|
| Red Collar | 200 | collar |
| Gold Collar | 500 | collar |
| Silk Bow | 200 | bow |
| Diamond Bow | 500 | bow |
| Wizard Hat 🧙 | 350 | hat |
| Party Hat 🎉 | 150 | hat |
| Crown 👑 | 800 | hat |
| Yarn Ball 🧶 | 200 | toy |
| Laser Pointer 🔴 | 300 | toy |
| Feather Wand 🪶 | 250 | toy |

### 🍬 Pet Candy (`category = 'candy'`)

Consumables stored in `inventory`. Used via `/pet candy [item]`. Quantity is decremented on each use.

| Item | Price | XP granted |
|---|---|---|
| XP Candy | 100 | 50 |
| Rare Candy | 300 | 200 |
| Mega Candy | 700 | 500 |

### 🎨 Profile Colors (`category = 'profile_color'`)

One-time purchases stored in `user_purchases`. Applied immediately on purchase (sets `users.profile_color`).

| Item | Price | Effect code |
|---|---|---|
| Cyan Theme | 400 | `color_cyan` |
| Rose Theme | 400 | `color_rose` |
| Midnight Theme | 400 | `color_midnight` |
| Custom Color | 1000 | `color_custom` |

Custom Color opens a modal where the user inputs a hex value (`#RRGGBB`). The value is stored in `users.custom_hex_color` and `users.profile_color` is set to `'custom'`.

---

## Effect Code Format

The `shop.effect` column holds a machine-readable string:

| Pattern | Meaning |
|---|---|
| `hunger_N` | Restore N hunger |
| `hap_N` / `happiness_N` | Restore N happiness |
| `hunger_N_hap_M` | Restore N hunger and M happiness |
| `color_NAME` | Unlock and apply profile color |
| `color_custom` | Open hex color modal |
| `auto_click` | Auto Clicker game upgrade |
| `double_points` | Double dabloon drops from Duck Clicker |
| `custom_x` / `custom_o` | Custom Tic Tac Toe symbol |
| `collar_xp_N` | Pet collar XP multiplier (not applied automatically) |
| `bow_dab_N` | Pet bow dabloon multiplier (not applied automatically) |
| `hat_cosmetic` | Hat cosmetic — no mechanical effect |
| `toy_happy` / `toy_zoomies` / `toy_hunt` | Sets cat message style |
| `pet_xp_N` | Grants N pet XP (candy) |

---

## Purchase Flow (`commands/shop.py`)

```
/shop buy [item]
  ├── look up item in shop table (case-insensitive)
  ├── check user balance
  │
  ├── category == 'games' or 'profile_color' (not custom)?
  │     ├── already purchased? → reject
  │     ├── deduct dabloons
  │     ├── insert into user_purchases
  │     └── if color: update users.profile_color
  │
  ├── effect == 'color_custom'?
  │     ├── purchase if not already owned
  │     └── open HexColorModal
  │
  └── everything else (pet_food, accessory, candy)?
        ├── deduct dabloons
        └── upsert into inventory (quantity += 1)
```

---

## Helper Functions (`commands/shop.py`)

| Function | What it does |
|---|---|
| `get_shop_items(category?)` | Returns all items, optionally filtered by category |
| `get_inventory(user_id)` | Returns items in inventory with quantity > 0 |
| `has_purchase(user_id, item_name)` | Returns True if user has an active one-time purchase |
| `add_to_inventory(user_id, item_name, qty)` | Upserts inventory row |
| `add_purchase(user_id, item_name, custom_value?)` | Inserts into user_purchases |
| `build_shop_embed(items, category_label, balance)` | Builds the shop embed |
