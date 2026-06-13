from utils.userbase.database import switch_pet_muted, switch_update_muted, get_user_info, list_users
from utils.amber import make_inbox_embed, OwnerView
from utils.userbase.owner import list_users
import utils.userbase.owner as owner
from discord import app_commands
import discord



@app_commands.allowed_contexts(guilds = True, dms = True, private_channels = True)
@app_commands.allowed_installs(guilds = True, users = True)
class AmberCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="amber",
            description="Commands related to the Amber bot itself.",
            guild_only=True,
        )


    @app_commands.command(name="mute_updates", description="Mute or unmute update notifications from the bot.")
    async def mute_updates(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        new_status = await switch_update_muted(user_id)
        status_text = "muted" if new_status else "unmuted"
        await interaction.response.send_message(f"Update notifications have been {status_text}.", ephemeral=True)

    @app_commands.command(name="mute_all_notif", description="Mute or unmute all notifications from the bot.")
    async def mute_all_notif(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        pet_status = switch_pet_muted(user_id)
        update_status = switch_update_muted(user_id)
        if pet_status and update_status:
            message = "All notifications have been muted."
        elif not pet_status and not update_status:
            message = "All notifications have been unmuted."
        elif pet_status and not update_status:
            message = "Pet notifications are muted, but update notifications are unmuted."
        else:
            message = "Pet notifications are unmuted, but update notifications are muted."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="inbox", description="send a message to the bot owner")
    @app_commands.describe(message="The message you want to send to the bot owner.")
    async def inbox(self, interaction: discord.Interaction, message: str):
        user_id = interaction.user.id
        user_info = await get_user_info(user_id)
        owners = await list_users()
        if not owners:
            await interaction.response.send_message("No bot owner is currently set up to receive messages.", ephemeral=True)
            return
        if not user_info:
            user_info = {
                "id": "unknown",
                "bio": "unknown",
                "level": 0,
                "amber_dabloons": 0,
                "total_actions": 0,
                "ttt_wins": 0,
                "ttt_streak": 0,
                "duck_clicker_score": 0
            }

        # create the record first so resolve works from the start
        inbox_id = await owner.create_inbox_message(user_id=user_id, message=message, interaction=interaction)
        inbox_data = await owner.get_inbox_message(inbox_id)

        is_sent_to_owners = True
        for owner_id in owners:
            o = interaction.client.get_user(owner_id)
            if o:
                try:
                    embed = make_inbox_embed(interaction.user, user_info, message)
                    view = OwnerView(o, inbox_data)  # pass inbox_data so resolve works
                    await o.send(embed=embed, view=view)
                except discord.Forbidden:
                    is_sent_to_owners = False
        if is_sent_to_owners:
            await interaction.response.send_message("Your message has been sent to the bot developers.", ephemeral=True)
        else:
            await interaction.response.send_message("Your message could not be sent to one or more developers due to privacy settings.", ephemeral=True)


async def amber_setup(bot):
    bot.tree.add_command(AmberCommands())
