import os
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite

from utils.radio.audio_processor import (
    download_from_youtube,
    download_from_spotify,
)

DB_PATH = "data/radio.db"


class RadioSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _sync_playlist(self, interaction, playlist_id, name, source_url, source_type):
        embed = discord.Embed(
            title="🔄 Syncing Playlist...",
            description=f"Downloading songs from **{name}**",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Source", value=source_type.upper())
        embed.set_footer(text="This may take a while...")
        await interaction.followup.send(embed=embed)

        if source_type == "youtube":
            success, songs, message = await download_from_youtube(source_url, playlist_id)
        elif source_type == "spotify":
            success, songs, message = await download_from_spotify(source_url, playlist_id)
        else:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="Unknown Source Type",
                    color=discord.Color.red(),
                )
            )
            return

        if not success:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="Sync Failed",
                    description=message,
                    color=discord.Color.red(),
                )
            )
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE playlists SET last_synced = CURRENT_TIMESTAMP WHERE id = ?",
                (playlist_id,),
            )
            await db.commit()

        final_embed = discord.Embed(
            title="✅ Sync Complete",
            description=f"**{name}** synced successfully!",
            color=discord.Color.green(),
        )
        final_embed.add_field(name="Songs Added", value=len(songs))

        if message:
            final_embed.add_field(
                name="Notice",
                value=message,
                inline=False,
            )

        final_embed.set_footer(text="Use /radio to start playing!")
        await interaction.edit_original_response(embed=final_embed)

    @app_commands.command(name="radio_add", description="Create a new radio playlist")
    @app_commands.describe(
        name="Name of your playlist",
        source_url="URL to playlist (Spotify/YouTube) - optional",
        public="Make playlist visible to server members",
    )
    async def set_radio(
        self,
        interaction: discord.Interaction,
        name: str,
        source_url: str | None = None,
        public: bool = False,
    ):
        await interaction.response.defer(thinking=True)

        source_type = None
        if source_url:
            if "spotify.com" in source_url:
                source_type = "spotify"
            elif "youtube.com" in source_url or "youtu.be" in source_url:
                source_type = "youtube"
            else:
                await interaction.followup.send("❌ Unsupported URL type!\nSupported: Spotify, YouTube")
                return

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id FROM playlists WHERE owner_id = ? AND name = ?",
                (interaction.user.id, name),
            )
            if await cursor.fetchone():
                await interaction.followup.send(
                    f"❌ You already have a playlist named **{name}**!"
                )
                return

            await db.execute(
                """
                INSERT INTO playlists (name, owner_id, is_public, source_url, source_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, interaction.user.id, public, source_url, source_type),
            )
            await db.commit()

            cursor = await db.execute("SELECT last_insert_rowid()")
            playlist_id = (await cursor.fetchone())[0]

        embed = discord.Embed(
            title="📻 Playlist Created!",
            description=f"**{name}** has been added to your radio library",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Playlist ID", value=f"`{playlist_id}`", inline=True)
        embed.add_field(
            name="Visibility",
            value="🌐 Public" if public else "🔒 Private",
            inline=True,
        )

        if source_url:
            embed.add_field(
                name="Source",
                value=f"[{source_type.upper()}]({source_url})",
                inline=False,
            )
            embed.set_footer(text="🔄 Auto-syncing playlist...")
        else:
            embed.set_footer(text="💡 Add songs manually or set a source URL later")

        await interaction.followup.send(embed=embed)

        if source_url:
            await self._sync_playlist(
                interaction,
                playlist_id,
                name,
                source_url,
                source_type,
            )

    @app_commands.command(name="radio_sync", description="Download songs from your playlist source")
    @app_commands.describe(playlist_id="The ID of the playlist to sync")
    async def sync_radio(self, interaction: discord.Interaction, playlist_id: int):
        await interaction.response.defer(thinking=True)

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT name, owner_id, source_url, source_type
                FROM playlists
                WHERE id = ?
                """,
                (playlist_id,),
            )
            playlist = await cursor.fetchone()

        if not playlist:
            await interaction.followup.send("❌ Playlist not found!")
            return

        name, owner_id, source_url, source_type = playlist

        if owner_id != interaction.user.id:
            await interaction.followup.send("❌ You don't own this playlist!")
            return

        if not source_url:
            await interaction.followup.send("❌ This playlist has no source URL set!")
            return

        await self._sync_playlist(
            interaction,
            playlist_id,
            name,
            source_url,
            source_type,
        )

    @app_commands.command(name="radio_remove", description="Remove a playlist and delete all its songs (owner only)")
    @app_commands.describe(playlist_id="ID of the playlist you want to remove")
    async def radio_remove(self, interaction: discord.Interaction, playlist_id: int):
        await interaction.response.defer(thinking=True)

        guild_id = interaction.guild_id
        radio_player_cog = interaction.client.get_cog("RadioPlayer")
        if radio_player_cog is None:
            await interaction.followup.send("❌ Radio player is not loaded.")
            return

        player = radio_player_cog.players.get(guild_id)


        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("SELECT owner_id FROM playlists WHERE id = ?", (playlist_id,))
            result = await cursor.fetchone()

            if not result:
                await interaction.followup.send("❌ Playlist not found!")
                return

            owner_id = result[0]
            if owner_id != interaction.user.id:
                await interaction.followup.send("❌ You can only delete your own playlists!")
                return

            cursor = await db.execute("SELECT file_path FROM songs WHERE playlist_id = ?", (playlist_id,))
            songs = await cursor.fetchall()

            for (file_path,) in songs:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

            await db.execute("DELETE FROM songs WHERE playlist_id = ?", (playlist_id,))
            await db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            await db.commit()

        if player and player.playlist_id == playlist_id:
            if player.voice_client and player.voice_client.is_playing():
                player.voice_client.stop()
            player.playlist_id = None
            player.playlist_name = None
            player.songs = []
            player.current_index = 0
            if player.message:
                embed = discord.Embed(
                    title="📻 Radio Player",
                    description="**Playlist removed!**\nSelect another playlist to play.",
                    color=discord.Color.red()
                )
                view = await radio_player_cog.create_player_view(guild_id, interaction.user.id)
                try:
                    await player.message.edit(embed=embed, view=view)
                except:
                    pass

        await interaction.followup.send(f"✅ Playlist `{playlist_id}` and its songs were removed successfully!")

    @app_commands.command(name="radio_libraries", description="View your radio playlists")
    async def my_playlists(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        
        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.is_public, p.source_type, COUNT(s.id) as song_count
                FROM playlists p
                LEFT JOIN songs s ON p.id = s.playlist_id
                WHERE p.owner_id = ?
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (interaction.user.id,))
            
            playlists = await cursor.fetchall()
        
        if not playlists:
            await interaction.followup.send("📻 You don't have any playlists yet! Use `/set_radio` to create one.")
            return
        
        embed = discord.Embed(
            title=f"📻 {interaction.user.display_name}'s Radio Playlists",
            color=discord.Color.blue()
        )
        
        for playlist_id, name, is_public, source_type, song_count in playlists:
            visibility = "🌐 Public" if is_public else "🔒 Private"
            source = f"📡 {source_type.upper()}" if source_type else "📝 Manual"
            value = f"{visibility} • {source} • {song_count} songs"
            embed.add_field(name=f"`{playlist_id}` • {name}", value=value, inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RadioSettings(bot))
