import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import asyncio

class RadioPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
    
    class PlayerState:
        def __init__(self):
            self.playlist_id = None
            self.playlist_name = None
            self.songs = []
            self.current_index = 0
            self.volume = 0.5
            self.loop = True
            self.loop_song = False
            self.mix_mode = False
            self.voice_client = None
            self.message = None
   
    async def get_user_playlists(self, user_id: int):
        """Get all playlists accessible to a user"""
        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.owner_id, COUNT(s.id) as song_count
                FROM playlists p
                LEFT JOIN songs s ON p.id = s.playlist_id
                WHERE (p.owner_id = ? OR p.is_public = 1)
                GROUP BY p.id
                HAVING song_count > 0
                ORDER BY p.name
            """, (user_id,))
            
            return await cursor.fetchall()
    
    @app_commands.command(name="radio", description="Start playing music from a playlist")
    @app_commands.describe(
        playlist_id="ID of the playlist to play (use /radio_libraries)",
        mix_mode="Randomly pick songs from random playlists"
    )
    async def radio(self, interaction: discord.Interaction, playlist_id: int = None, mix_mode: bool = False):
        await interaction.response.defer()
        
        if not interaction.user.voice:
            await interaction.followup.send("❌ You need to be in a voice channel to use the radio!")
            return
        
        voice_channel = interaction.user.voice.channel
        
        guild_id = interaction.guild_id
        if guild_id not in self.players:
            self.players[guild_id] = self.PlayerState()
        
        player = self.players[guild_id]
        player.mix_mode = mix_mode
        player.user_id = interaction.user.id
        
        if mix_mode:
            async with aiosqlite.connect("data/radio.db") as db:
                cursor = await db.execute("""
                    SELECT p.id, p.name, COUNT(s.id) as song_count
                    FROM playlists p
                    LEFT JOIN songs s ON p.id = s.playlist_id
                    WHERE (p.owner_id = ? OR p.is_public = 1)
                    GROUP BY p.id
                    HAVING song_count > 0
                """, (interaction.user.id,))
                
                playlists = await cursor.fetchall()
            
            if not playlists:
                await interaction.followup.send("No playlists available for mix mode!")
                return
            
            playlist_id, playlist_name, _ = random.choice(playlists)
            player.playlist_id = playlist_id
            player.playlist_name = f"{playlist_name} (Mix Mode)"
            
        else:
            if not playlist_id:
                await interaction.followup.send("Please specify a playlist ID or enable mix mode!")
                return
            
            async with aiosqlite.connect("data/radio.db") as db:
                cursor = await db.execute("""
                    SELECT name, owner_id, is_public
                    FROM playlists
                    WHERE id = ?
                """, (playlist_id,))
                
                playlist = await cursor.fetchone()
                
                if not playlist:
                    await interaction.followup.send("Playlist not found!")
                    return
                
                name, owner_id, is_public = playlist
                
                if owner_id != interaction.user.id and not is_public:
                    await interaction.followup.send("This playlist is private!")
                    return
                
                player.playlist_id = playlist_id
                player.playlist_name = name
        
        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("""
                SELECT id, title, artist, file_path, duration
                FROM songs
                WHERE playlist_id = ?
                ORDER BY added_at
            """, (player.playlist_id,))
            
            player.songs = await cursor.fetchall()
        
        if not player.songs:
            await interaction.followup.send("❌ This playlist has no songs!")
            return
        
        if mix_mode:
            random.shuffle(player.songs)
        
        player.current_index = 0
        
        try:
            if player.voice_client and player.voice_client.is_connected():
                await player.voice_client.move_to(voice_channel)
            else:
                player.voice_client = await voice_channel.connect()
        except Exception as e:
            await interaction.followup.send(f"❌ Could not connect to voice channel: {e}")
            return
        
        embed = self.create_player_embed(player)
        view = await self.create_player_view(guild_id, interaction.user.id)
        
        message = await interaction.followup.send(embed=embed, view=view)
        player.message = message
        
        await self.play_current_song(guild_id)
    
    def create_player_embed(self, player):
        """Create the player control embed"""
        embed = discord.Embed(
            title="📻 Radio Player",
            color=discord.Color.blue()
        )
        
        if player.songs and player.current_index < len(player.songs):
            song_id, title, artist, file_path, duration = player.songs[player.current_index]
            
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            embed.description = f"**{title}**\nby {artist}"
            embed.add_field(name="Playlist", value=player.playlist_name, inline=True)
            embed.add_field(name="Track", value=f"{player.current_index + 1}/{len(player.songs)}", inline=True)
            embed.add_field(name="Duration", value=duration_str, inline=True)
        else:
            embed.description = "**Nothing is playing**"
            embed.add_field(name="Playlist", value=player.playlist_name or "No playlist selected", inline=True)
            embed.add_field(name="Track", value="—", inline=True)
            embed.add_field(name="Duration", value="—", inline=True)
        
        status = []
        if player.loop_song:
            status.append("🔂 Loop Song")
        elif player.loop:
            status.append("🔁 Loop Playlist")
        else:
            status.append("➡️ No Loop")
        
        if player.mix_mode:
            status.append("🎲 Mix")
        status.append(f"🔊 {int(player.volume * 100)}%")
        
        embed.set_footer(text=" • ".join(status))
        
        return embed
    
    async def create_player_view(self, guild_id, user_id):
        """Create the button view with playlist dropdown, including public server playlists"""
        view = discord.ui.View(timeout=None)

        user_playlists = await self.get_user_playlists(user_id)

        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.owner_id, COUNT(s.id) as song_count
                FROM playlists p
                LEFT JOIN songs s ON p.id = s.playlist_id
                WHERE p.is_public = 1 AND p.owner_id != ?
                GROUP BY p.id
                HAVING song_count > 0
                ORDER BY p.name
            """, (user_id,))
            public_playlists = await cursor.fetchall()

        all_playlists = {p[0]: p for p in user_playlists}  # key = playlist_id
        for p in public_playlists:
            if p[0] not in all_playlists:
                all_playlists[p[0]] = p

        options = []
        for playlist_id, name, owner_id, song_count in list(all_playlists.values())[:25]:
            label = name[:100]
            description = f"{song_count} songs"
            if owner_id != user_id:
                description += " • Public"
            options.append(discord.SelectOption(
                label=label,
                value=str(playlist_id),
                description=description
            ))

        if options:
            playlist_select = discord.ui.Select(
                placeholder="🎵 Choose a playlist...",
                options=options,
                custom_id=f"radio_playlist_{guild_id}",
                row=0
            )
            playlist_select.callback = self.select_playlist
            view.add_item(playlist_select)

        back_button = discord.ui.Button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id=f"radio_back_{guild_id}", row=1)
        play_button = discord.ui.Button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id=f"radio_play_{guild_id}", row=1)
        next_button = discord.ui.Button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id=f"radio_next_{guild_id}", row=1)
        vol_down_button = discord.ui.Button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id=f"radio_voldown_{guild_id}", row=2)
        loop_button = discord.ui.Button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id=f"radio_loop_{guild_id}", row=2)
        vol_up_button = discord.ui.Button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id=f"radio_volup_{guild_id}", row=2)
        stop_button = discord.ui.Button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id=f"radio_stop_{guild_id}", row=2)

        back_button.callback = self.button_back
        play_button.callback = self.button_play_pause
        next_button.callback = self.button_next
        vol_down_button.callback = self.button_vol_down
        loop_button.callback = self.button_loop
        vol_up_button.callback = self.button_vol_up
        stop_button.callback = self.button_stop

        view.add_item(back_button)
        view.add_item(play_button)
        view.add_item(next_button)
        view.add_item(vol_down_button)
        view.add_item(loop_button)
        view.add_item(vol_up_button)
        view.add_item(stop_button)

        return view
    
    async def select_playlist(self, interaction: discord.Interaction):
        """Handle playlist selection from dropdown"""
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if not player:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
            return
        
        playlist_id = int(interaction.data['values'][0])
        
        async with aiosqlite.connect("data/radio.db") as db:
            cursor = await db.execute("""
                SELECT name, owner_id, is_public
                FROM playlists
                WHERE id = ?
            """, (playlist_id,))
            
            playlist = await cursor.fetchone()
            
            if not playlist:
                await interaction.response.send_message("❌ Playlist not found!", ephemeral=True)
                return
            
            name, owner_id, is_public = playlist
            
            if owner_id != interaction.user.id and not is_public:
                await interaction.response.send_message("❌ This playlist is private!", ephemeral=True)
                return
            
            cursor = await db.execute("""
                SELECT id, title, artist, file_path, duration
                FROM songs
                WHERE playlist_id = ?
                ORDER BY added_at
            """, (playlist_id,))
            
            songs = await cursor.fetchall()
        
        if not songs:
            await interaction.response.send_message("❌ This playlist has no songs!", ephemeral=True)
            return
        
        # Update player state
        player.playlist_id = playlist_id
        player.playlist_name = name
        player.songs = songs
        player.current_index = 0
        
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
        
        await self.play_current_song(guild_id)
        
        await interaction.response.send_message(f"✅ Switched to playlist: **{name}**", ephemeral=True)
    
    async def play_current_song(self, guild_id):
        player = self.players.get(guild_id)
        if not player or not player.voice_client:
            return

        if player.voice_client.is_playing() or player.voice_client.is_paused():
            return

        if player.current_index >= len(player.songs):
            if player.loop:
                player.current_index = 0
            else:
                # End of playlist - update embed but keep controls
                if player.message:
                    embed = self.create_player_embed(player)
                    view = await self.create_player_view(guild_id, player.user_id)
                    try:
                        await player.message.edit(embed=embed, view=view)
                    except:
                        pass
                return

        song_id, title, artist, file_path, duration = player.songs[player.current_index]

        def after_playing(error):
            if error:
                print(f"Playback error: {error}")

            fut = asyncio.run_coroutine_threadsafe(
                self.advance_to_next(guild_id),
                self.bot.loop
            )
            try:
                fut.result()
            except Exception as e:
                print(f"Advance error: {e}")

        try:
            source = discord.FFmpegPCMAudio(file_path)
            source = discord.PCMVolumeTransformer(source, volume=player.volume)
            player.voice_client.play(source, after=after_playing)
        except Exception as e:
            print(f"Error starting playback: {e}")
            return

        if player.message:
            embed = self.create_player_embed(player)
            view = await self.create_player_view(guild_id, player.user_id)
            try:
                await player.message.edit(embed=embed, view=view)
            except:
                pass
    
    async def advance_to_next(self, guild_id):
        player = self.players.get(guild_id)
        if not player:
            return
        
        if player.loop_song:
            await self.play_current_song(guild_id)
            return

        if player.current_index + 1 >= len(player.songs):
            if player.loop:
                player.current_index = 0
            else:
                player.current_index += 1  # Move past end to trigger "nothing playing"
                await self.play_current_song(guild_id)
                return
        else:
            player.current_index += 1

        await self.play_current_song(guild_id)
    
    async def button_back(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)

        if not player or not player.voice_client:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
            return

        if player.current_index > 0:
            player.current_index -= 1
            player.voice_client.stop()
            await interaction.response.defer()
        else:
            await interaction.response.send_message("⏮️ Already at first song!", ephemeral=True)
    
    async def button_play_pause(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if player and player.voice_client:
            if player.voice_client.is_playing():
                player.voice_client.pause()
                await interaction.response.send_message("⏸️ Paused", ephemeral=True)
            elif player.voice_client.is_paused():
                player.voice_client.resume()
                await interaction.response.send_message("▶️ Resumed", ephemeral=True)
            else:
                # Nothing playing, try to start
                await self.play_current_song(guild_id)
                await interaction.response.send_message("▶️ Started playing", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
    
    async def button_next(self, interaction: discord.Interaction):
        player = self.players.get(interaction.guild_id)

        if not player or not player.voice_client:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
            return

        player.voice_client.stop()
        if player.current_index + 1 >= len(player.songs):
            if player.loop:
                player.current_index = 0
            else:
                await interaction.response.send_message("⏭️ End of playlist!", ephemeral=True)
                return
        else:
            player.current_index += 1

        await self.play_current_song(interaction.guild_id)
        await interaction.response.defer()
    
    async def button_vol_down(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if player:
            player.volume = max(0.0, player.volume - 0.1)
            if player.voice_client and player.voice_client.source:
                player.voice_client.source.volume = player.volume
            
            if player.message:
                embed = self.create_player_embed(player)
                view = await self.create_player_view(guild_id, player.user_id)
                try:
                    await player.message.edit(embed=embed, view=view)
                except:
                    pass
            
            await interaction.response.send_message(f"🔉 Volume: {int(player.volume * 100)}%", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
    
    async def button_loop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if player:
            if player.loop and not player.loop_song:
                player.loop_song = True
                player.loop = False
                status = "🔂 Looping current song"
            elif player.loop_song:
                player.loop_song = False
                player.loop = False
                status = "➡️ Loop disabled"
            else:
                player.loop = True
                player.loop_song = False
                status = "🔁 Looping playlist"
            
            if player.message:
                embed = self.create_player_embed(player)
                view = await self.create_player_view(guild_id, player.user_id)
                try:
                    await player.message.edit(embed=embed, view=view)
                except:
                    pass
            
            await interaction.response.send_message(status, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
    
    async def button_vol_up(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if player:
            player.volume = min(1.0, player.volume + 0.1)
            if player.voice_client and player.voice_client.source:
                player.voice_client.source.volume = player.volume
            
            if player.message:
                embed = self.create_player_embed(player)
                view = await self.create_player_view(guild_id, player.user_id)
                try:
                    await player.message.edit(embed=embed, view=view)
                except:
                    pass
            
            await interaction.response.send_message(f"🔊 Volume: {int(player.volume * 100)}%", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
    
    async def button_stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)
        
        if not player or not player.voice_client:
            await interaction.response.send_message("❌ No active player", ephemeral=True)
            return
        
        if player.voice_client.is_playing() or player.voice_client.is_paused():
            player.voice_client.stop()
        
        await player.voice_client.disconnect()
        
        if player.message:
            embed = discord.Embed(
                title="📻 Radio Player",
                description="**Radio Stopped**\n\nSelect a playlist to start playing!",
                color=discord.Color.red()
            )
            embed.set_footer(text="Choose a playlist from the dropdown above")
            
            view = await self.create_player_view(guild_id, player.user_id)
            try:
                await player.message.edit(embed=embed, view=view)
            except:
                pass
        
        user_id = player.user_id
        self.players[guild_id] = self.PlayerState()
        self.players[guild_id].user_id = user_id
        
        await interaction.response.send_message("⏹️ Radio stopped!", ephemeral=True)


    @app_commands.command(name="radio_stop", description="Stop the radio and disconnect from voice")
    async def radio_stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild_id = interaction.guild_id
        player = self.players.get(guild_id)

        if not player:
            await interaction.followup.send("❌ No active radio player!")
            return

        if not player.voice_client or not player.voice_client.is_connected():
            await interaction.followup.send("❌ Not connected to voice!")
            return

        if player.voice_client.is_playing() or player.voice_client.is_paused():
            player.voice_client.stop()
        await player.voice_client.disconnect()

        if player.message:
            embed = discord.Embed(
                title="📻 Radio Player",
                description="**Radio Stopped**\n\nSelect a playlist to start playing!",
                color=discord.Color.red()
            )
            embed.set_footer(text="Choose a playlist from the dropdown above")
            view = await self.create_player_view(guild_id, player.user_id or interaction.user.id)
            try:
                await player.message.edit(embed=embed, view=view)
            except:
                pass

        user_id = player.user_id or interaction.user.id
        self.players[guild_id] = self.PlayerState()
        self.players[guild_id].user_id = user_id


        await interaction.followup.send("⏹️ Radio stopped and disconnected!")
async def setup(bot):
    await bot.add_cog(RadioPlayer(bot))
