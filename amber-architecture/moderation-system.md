# Moderation System

All admin and server management commands. Guild-only. Lives in `commands/moderation.py` as `ModerationCog`.

---

## Overview

`ModerationCog` handles two slash command groups: `/admin` (member actions) and `/server` (guild configuration). It also listens to `on_member_join` to send welcome messages and assign autoroles.

All mod actions are logged to the configured log channel if one is set.

---

## Shared Infrastructure

### `can_moderate_member(interaction, member)`

Safety check run before every moderation action. Returns `False` (and sends an ephemeral error) if:
- Command is used outside a guild.
- Bot is not a guild member (user-installed app in a foreign server).
- Target is the invoker themselves.
- Target is the server owner.
- Target's highest role is >= the bot's highest role.

### `create_mod_embed(member, interaction, title, reason, color)`

Builds a consistent embed for kick, ban, timeout, warn actions. Includes:
- Time in server (if `member.joined_at` is available)
- Reason
- Action timestamp
- Invoker's avatar as author

### `send_log(guild_id, embed)`

Fetches `guild_config.log_channel_id` and sends the embed there. Silent no-op if no channel is set or the channel no longer exists.

### `log_warning(guild_id, user_id, moderator_id, reason)`

Inserts a row into `warnings`.

### `get_warnings(guild_id, user_id)` / `delete_warnings(guild_id, user_id)`

Read and delete warnings for a member.

---

## Admin Commands

All commands in the `/admin` group are guild-only and require explicit Discord permissions.

### `/admin kick [member] [reason?]`

Kicks a member. Runs safety check. Logs action.

### `/admin ban [member] [reason?]`

Bans a member. Runs safety check. Logs action.

### `/admin unban [user_id] [reason?]`

Unbans by raw Discord user ID (string input, validated to int). Uses `bot.fetch_user()` for uncached users. Logs action.

### `/admin timeout [member] [duration] [reason?]`

Duration string format: `10m`, `2h`, `1d`. Parsed into seconds then passed as `datetime.timedelta` to `member.timeout()`. Runs safety check. Logs action.

Valid units: `s`, `m`, `h`, `d`.

### `/admin warn [member] [reason?]`

Logs a warning to the `warnings` table. Sends a yellow warning embed. Logs action.

### `/admin warnings [member]`

Fetches all warnings for a member ordered newest-first. Resolves moderator user objects via `bot.get_user()` or `bot.fetch_user()`. Read-only — not logged.

### `/admin clear_warnings [member]`

Deletes all warning rows for a member in this guild. Logs action.

### `/admin purge [n] [user?]`

Bulk-deletes up to 100 messages. Optional user filter. Sends ephemeral response **before** purging (prevents 404 on followup). Logs action with count and optional target user.

### `/admin slowmode [seconds]`

Sets channel slowmode delay 0–21600 (6 hours). 0 disables. Logs action.

### `/admin lockdown`

Toggles `@everyone`'s `send_messages` permission on the current channel. If already locked (`False`), resets to `None` (inherits). Logs action with appropriate color (orange for lock, green for unlock).

### `/admin unlockdown`

Always lifts lockdown (sets `send_messages = None`). Separate from lockdown toggle for explicit usage. Logs action.

---

## Server Commands

### `/server info`

Sends an embed with: owner, member count, text/voice channel counts, role count, creation date.

### `/server invite`

Creates a single-use, 1-hour invite via the first text channel.

### `/server icon` / `/server banner`

Shows the server icon or banner as an embed image. Sends an error if none exists.

### `/server set_prefix [prefix]`

Sets a custom command prefix (1–5 chars) in `guild_config`. Uses upsert (`INSERT OR IGNORE ... ON CONFLICT DO UPDATE`). Logs action.

### `/server set_welcome [channel]`

Checks that the bot can send in the channel, then opens `WelcomeMessageModal` for the admin to enter the welcome message template.

Placeholders: `{user}` (mentions new member), `{server}` (server name).

### `/server set_welcome_off`

Sets `welcome_channel_id = NULL` in `guild_config`. Logs action.

### `/server set_autorole [role]`

Validates that the role is below the bot's highest role and isn't `@everyone`. Upserts `autorole_id` in `guild_config`. Logs action.

### `/server set_autorole_off`

Sets `autorole_id = NULL` in `guild_config`. Logs action.

### `/server set_log [channel]`

Validates bot can send in the channel. Upserts `log_channel_id`. Immediately sends a test embed to confirm it works.

---

## Welcome & Autorole (`on_member_join`)

When a member joins:

1. Fetch `guild_config` for the guild.
2. If `welcome_channel_id` is set: send the welcome message (with `{user}` and `{server}` replaced) to that channel.
3. If `autorole_id` is set: assign the role via `member.add_roles()`. Silently ignores `Forbidden` (bot lost permission).

---

## Error Handling

`cog_app_command_error` catches all app command errors in the cog and sends a user-friendly ephemeral message. Also prints the full traceback to console for debugging. Handles `MissingPermissions` with a specific message.
