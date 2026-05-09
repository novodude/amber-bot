import asyncio
import discord
import aiosqlite
from discord import app_commands
from discord.ext import commands

from utils.radio.audio_processor import (
    sync_playlist_background,
    resolve_stream_url,
    build_progress_embed,
)

DB_PATH = "data/radio.db"
FFMPEG_STREAM_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
)


# ── Player state ───────────────────────────────────────────────────────────────

class PlayerState:
    def __init__(self):
        self.playlist_id: int | None = None
        self.playlist_name: str = "Unknown"
        self.songs: list[tuple] = []          # (id, title, artist, stream_url, duration)
        self.current_index: int = 0
        self.volume: float = 0.5
        self.loop: bool = True
        self.loop_song: bool = False
        self.mix_mode: bool = False
        self.voice_client: discord.VoiceClient | None = None
        self.message: discord.Message | None = None
        self._keepalive_task: asyncio.Task | None = None
        self.user_id: int | None = None


# ── Song paginator (for /radio songs) ─────────────────────────────────────────

class SongsPaginator(discord.ui.View):
    def __init__(self, songs: list, playlist_name: str, user_id: int):
        super().__init__(timeout=None)
        self.songs = songs
        self.playlist_name = playlist_name
        self.user_id = user_id
        self.page = 0
        self.per_page = 10
        self.max_page = max(0, (len(songs) - 1) // self.per_page)

    def build_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        page_songs = self.songs[start:start + self.per_page]
        embed = discord.Embed(
            title=f"🎶 {self.playlist_name}",
            description=f"Page {self.page + 1}/{self.max_page + 1}",
            color=discord.Color.blurple(),
        )
        for idx, (title, artist, duration) in enumerate(page_songs, start=start + 1):
            mins, secs = divmod(duration or 0, 60)
            embed.add_field(
                name=f"{idx}. {title}",
                value=f"👤 {artist or 'Unknown'} • ⏱ {mins}:{secs:02d}",
                inline=False,
            )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your controls!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(self.page - 1, 0)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.page + 1, self.max_page)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ── Player UI ──────────────────────────────────────────────────────────────────

class RadioCommands(app_commands.Group):
    """All radio commands. Audio is streamed directly — nothing is saved to disk."""

    def __init__(self):
        super().__init__(name="radio", description="Streaming radio commands")
        self.players: dict[int, PlayerState] = {}

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_player(self, guild_id: int) -> PlayerState:
        if guild_id not in self.players:
            self.players[guild_id] = PlayerState()
        return self.players[guild_id]

    def _create_embed(self, player: PlayerState) -> discord.Embed:
        embed = discord.Embed(title="📻 Radio Player", color=discord.Color.blue())
        if player.songs and player.current_index < len(player.songs):
            _, title, artist, _, duration = player.songs[player.current_index]
            mins, secs = divmod(duration or 0, 60)
            embed.description = f"**{title}**\nby {artist or 'Unknown'}"
            embed.add_field(name="Playlist", value=player.playlist_name, inline=True)
            embed.add_field(name="Track", value=f"{player.current_index + 1}/{len(player.songs)}", inline=True)
            embed.add_field(name="Duration", value=f"{mins}:{secs:02d}", inline=True)
        else:
            embed.description = "**Nothing playing** — use `/radio play` to start."
        status = []
        status.append("🔂 Loop Song" if player.loop_song else "🔁 Loop Playlist" if player.loop else "➡️ No Loop")
        if player.mix_mode:
            status.append("🎲 Mix")
        status.append(f"🔊 {int(player.volume * 100)}%")
        embed.set_footer(text=" • ".join(status))
        return embed

    async def _create_view(self, guild_id: int, user_id: int) -> discord.ui.View:
        player = self._get_player(guild_id)
        view = discord.ui.View(timeout=None)

        # Playlist dropdown
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.owner_id, COUNT(s.id) as cnt
                FROM playlists p
                LEFT JOIN songs s ON p.id = s.playlist_id
                WHERE p.owner_id = ? OR p.is_public = 1
                GROUP BY p.id HAVING cnt > 0 ORDER BY p.name LIMIT 25
            """, (user_id,))
            playlists = await cursor.fetchall()

        if playlists:
            options = [
                discord.SelectOption(
                    label=name[:100],
                    value=str(pid),
                    description=f"{cnt} songs" + (" • Public" if owner != user_id else ""),
                )
                for pid, name, owner, cnt in playlists
            ]
            select = discord.ui.Select(
                placeholder="🎵 Choose a playlist...",
                options=options,
                custom_id=f"radio_playlist_{guild_id}",
                row=0,
            )
            select.callback = self._select_playlist_callback
            view.add_item(select)

        def _make_btn(emoji, style, cid, cb, row):
            b = discord.ui.Button(emoji=emoji, style=style, custom_id=cid, row=row)
            b.callback = cb
            return b

        view.add_item(_make_btn("⏮️", discord.ButtonStyle.secondary, f"radio_back_{guild_id}",   self._btn_back,       1))
        view.add_item(_make_btn("⏸️", discord.ButtonStyle.primary,   f"radio_play_{guild_id}",   self._btn_playpause,  1))
        view.add_item(_make_btn("⏭️", discord.ButtonStyle.secondary, f"radio_next_{guild_id}",   self._btn_next,       1))
        view.add_item(_make_btn("🔉", discord.ButtonStyle.secondary, f"radio_vold_{guild_id}",   self._btn_vol_down,   2))
        view.add_item(_make_btn("🔁", discord.ButtonStyle.secondary, f"radio_loop_{guild_id}",   self._btn_loop,       2))
        view.add_item(_make_btn("🔊", discord.ButtonStyle.secondary, f"radio_volu_{guild_id}",   self._btn_vol_up,     2))
        view.add_item(_make_btn("⏹️", discord.ButtonStyle.danger,    f"radio_stop_{guild_id}",   self._btn_stop,       2))
        return view

    async def _keepalive_loop(self, guild_id: int):
        """Re-edits the player message every 5 minutes to keep buttons alive."""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            player = self._get_player(guild_id)
            if not player.voice_client or not player.message:
                break
            await self._update_message(guild_id)

    async def _play_current(self, guild_id: int):
        player = self._get_player(guild_id)
        if not player.voice_client or player.voice_client.is_playing() or player.voice_client.is_paused():
            return
        if not player.songs:
            return

        if player.current_index >= len(player.songs):
            if player.loop:
                player.current_index = 0
            else:
                await self._update_message(guild_id)
                return

        _, title, artist, watch_url, duration = player.songs[player.current_index]

        # Resolve the real audio stream URL on-the-fly
        stream_url = await resolve_stream_url(watch_url)
        if not stream_url:
            # Skip broken track
            player.current_index += 1
            await self._play_current(guild_id)
            return

        # Capture the event loop now, before the thread callback fires
        event_loop = asyncio.get_event_loop()

        def after_playing(error):
            if error:
                print(f"[radio] playback error: {error}")
            asyncio.run_coroutine_threadsafe(self._advance(guild_id), event_loop)

        src = discord.FFmpegPCMAudio(stream_url, before_options=FFMPEG_STREAM_OPTIONS)
        source = discord.PCMVolumeTransformer(src, volume=player.volume)
        player.voice_client.play(source, after=after_playing)

        # start keepalive only if not already running
        if not getattr(player, '_keepalive_task', None) or player._keepalive_task.done():
            player._keepalive_task = asyncio.create_task(self._keepalive_loop(guild_id))

        await self._update_message(guild_id)

    async def _advance(self, guild_id: int):
        player = self._get_player(guild_id)

        if player.loop_song:
            await self._play_current(guild_id)
            return

        # advance to next track
        if player.current_index + 1 >= len(player.songs):
            player.current_index = 0 if player.loop else len(player.songs)
        else:
            player.current_index += 1

        await self._play_current(guild_id)

    async def _update_message(self, guild_id: int):
        player = self._get_player(guild_id)
        if not player.message:
            return
        try:
            embed = self._create_embed(player)
            view = await self._create_view(guild_id, player.user_id)
            await player.message.edit(embed=embed, view=view)
        except Exception:
            pass

    async def _ensure_voice(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice:
            await interaction.followup.send("❌ Join a voice channel first!", ephemeral=True)
            return False
        return True

    # ── Button callbacks ───────────────────────────────────────────────────────

    async def _select_playlist_callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        playlist_id = int(interaction.data["values"][0])

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name, owner_id, is_public FROM playlists WHERE id = ?", (playlist_id,)
            )
            row = await cursor.fetchone()
            if not row:
                await interaction.response.send_message("Playlist not found!", ephemeral=True)
                return
            name, owner_id, is_public = row
            if owner_id != interaction.user.id and not is_public:
                await interaction.response.send_message("That playlist is private!", ephemeral=True)
                return
            cursor = await db.execute(
                "SELECT id, title, artist, stream_url, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
                (playlist_id,),
            )
            songs = await cursor.fetchall()

        if not songs:
            await interaction.response.send_message("That playlist has no songs!", ephemeral=True)
            return

        player.playlist_id = playlist_id
        player.playlist_name = name
        player.songs = songs
        player.current_index = 0

        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()

        await self._play_current(guild_id)
        await interaction.response.send_message(f"▶️ Switched to **{name}**", ephemeral=True)

    async def _btn_back(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if not player.voice_client:
            await interaction.response.send_message("No active player.", ephemeral=True)
            return
        if player.current_index > 0:
            player.current_index -= 1
            player.voice_client.stop()
        await interaction.response.defer()

    async def _btn_playpause(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if player.voice_client:
            if player.voice_client.is_playing():
                player.voice_client.pause()
                await interaction.response.send_message("⏸️ Paused", ephemeral=True)
            elif player.voice_client.is_paused():
                player.voice_client.resume()
                await interaction.response.send_message("▶️ Resumed", ephemeral=True)
            else:
                await self._play_current(interaction.guild_id)
                await interaction.response.send_message("▶️ Playing", ephemeral=True)
        else:
            await interaction.response.send_message("No active player.", ephemeral=True)

    async def _btn_next(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if not player.voice_client:
            await interaction.response.send_message("No active player.", ephemeral=True)
            return

        player.voice_client.stop()
        await interaction.response.defer()

    async def _btn_vol_down(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        player.volume = max(0.0, player.volume - 0.1)
        if player.voice_client and player.voice_client.source:
            player.voice_client.source.volume = player.volume
        await self._update_message(interaction.guild_id)
        await interaction.response.send_message(f"🔉 {int(player.volume * 100)}%", ephemeral=True)

    async def _btn_vol_up(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        player.volume = min(1.0, player.volume + 0.1)
        if player.voice_client and player.voice_client.source:
            player.voice_client.source.volume = player.volume
        await self._update_message(interaction.guild_id)
        await interaction.response.send_message(f"🔊 {int(player.volume * 100)}%", ephemeral=True)

    async def _btn_loop(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if player.loop and not player.loop_song:
            player.loop_song, player.loop = True, False
            msg = "🔂 Looping current song"
        elif player.loop_song:
            player.loop_song, player.loop = False, False
            msg = "➡️ Loop off"
        else:
            player.loop = True
            msg = "🔁 Looping playlist"
        await self._update_message(interaction.guild_id)
        await interaction.response.send_message(msg, ephemeral=True)

    async def _btn_stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        if player.voice_client:
            if player.voice_client.is_playing() or player.voice_client.is_paused():
                player.voice_client.stop()
            await player.voice_client.disconnect()
        self.players[guild_id] = PlayerState()
        await interaction.response.send_message("⏹️ Stopped.", ephemeral=True)

    # ── Slash commands ─────────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Play a playlist or stream a single YouTube/Spotify URL")
    @app_commands.describe(
        playlist_id="ID of a saved playlist to play",
        source_url="Stream a single YouTube URL directly",
        mix_mode="Shuffle songs from all your accessible playlists",
    )
    @app_commands.guild_only()
    async def play(
        self,
        interaction: discord.Interaction,
        playlist_id: int | None = None,
        source_url: str | None = None,
        mix_mode: bool = False,
    ):
        await interaction.response.defer()
        if not await self._ensure_voice(interaction):
            return

        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        player.user_id = interaction.user.id
        player.mix_mode = mix_mode

        voice_channel = interaction.user.voice.channel
        try:
            if player.voice_client and player.voice_client.is_connected():
                await player.voice_client.move_to(voice_channel)
            else:
                player.voice_client = await voice_channel.connect()
        except Exception as e:
            await interaction.followup.send(f"❌ Could not connect: {e}")
            return

        # ── Single URL streaming ───────────────────────────────────────────────
        if source_url:
            await interaction.followup.send("🔍 Resolving stream...", ephemeral=True)

            stream_url = await resolve_stream_url(source_url)
            if not stream_url:
                await interaction.followup.send("❌ Couldn't resolve that URL.")
                return

            def after(error):
                pass

            src = discord.FFmpegPCMAudio(stream_url, before_options=FFMPEG_STREAM_OPTIONS)
            source = discord.PCMVolumeTransformer(src, volume=player.volume)
            if player.voice_client.is_playing():
                player.voice_client.stop()
            player.voice_client.play(source, after=after)
            await interaction.followup.send(f"▶️ Streaming `{source_url}`")
            return

        # ── Mix mode ───────────────────────────────────────────────────────────
        if mix_mode:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("""
                    SELECT s.id, s.title, s.artist, s.stream_url, s.duration
                    FROM songs s
                    JOIN playlists p ON s.playlist_id = p.id
                    WHERE p.owner_id = ? OR p.is_public = 1
                    ORDER BY RANDOM()
                """, (interaction.user.id,))
                player.songs = await cursor.fetchall()
            if not player.songs:
                await interaction.followup.send("❌ No songs available for mix mode!")
                return
            player.playlist_name = "🎲 Mix Mode"
            player.current_index = 0
            embed = self._create_embed(player)
            view = await self._create_view(guild_id, interaction.user.id)
            player.message = await interaction.followup.send(embed=embed, view=view)
            await self._play_current(guild_id)
            return

        # ── Playlist mode ──────────────────────────────────────────────────────
        if not playlist_id:
            await interaction.followup.send("❌ Provide a `playlist_id`, a `source_url`, or enable `mix_mode`.")
            return

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name, owner_id, is_public FROM playlists WHERE id = ?", (playlist_id,)
            )
            row = await cursor.fetchone()
            if not row:
                await interaction.followup.send("❌ Playlist not found!")
                return
            name, owner_id, is_public = row
            if owner_id != interaction.user.id and not is_public:
                await interaction.followup.send("❌ That playlist is private!")
                return
            cursor = await db.execute(
                "SELECT id, title, artist, stream_url, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
                (playlist_id,),
            )
            player.songs = await cursor.fetchall()

        if not player.songs:
            await interaction.followup.send("❌ That playlist has no songs!")
            return

        player.playlist_id = playlist_id
        player.playlist_name = name
        player.current_index = 0

        embed = self._create_embed(player)
        view = await self._create_view(guild_id, interaction.user.id)
        player.message = await interaction.followup.send(embed=embed, view=view)
        await self._play_current(guild_id)

    @app_commands.command(name="queue", description="Add a YouTube URL to the current queue without interrupting playback")
    @app_commands.describe(source_url="YouTube URL to queue")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction, source_url: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild_id
        player = self._get_player(guild_id)

        if not player.voice_client or not player.songs:
            await interaction.followup.send("❌ Nothing is playing. Use `/radio play` first.", ephemeral=True)
            return

        opts = {'format': 'bestaudio/best', 'quiet': True, 'skip_download': True, 'no_warnings': True}
        import yt_dlp

        def sync():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(source_url, download=False)

        import asyncio
        info = await asyncio.get_event_loop().run_in_executor(None, sync)
        if not info:
            await interaction.followup.send("❌ Couldn't resolve that URL.", ephemeral=True)
            return

        video_id = info.get("id", "")
        title = info.get("title", "Unknown Title")
        watch_url = f"https://www.youtube.com/watch?v={video_id}"

        player.songs.append((None, title, info.get("uploader"), watch_url, info.get("duration", 0)))
        await interaction.followup.send(f"✅ **{title}** added to queue (position {len(player.songs)})", ephemeral=True)
        await self._update_message(guild_id)

    @app_commands.command(name="stop", description="Stop playback and disconnect from voice")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        if not player.voice_client:
            await interaction.response.send_message("❌ Not connected.", ephemeral=True)
            return
        if player.voice_client.is_playing() or player.voice_client.is_paused():
            player.voice_client.stop()
        await player.voice_client.disconnect()
        self.players[guild_id] = PlayerState()
        await interaction.response.send_message("⏹️ Radio stopped.")

    @app_commands.command(name="add", description="Create a new playlist from a YouTube or Spotify URL")
    @app_commands.describe(
        name="Name for your playlist",
        source_url="YouTube or Spotify playlist/track URL",
        public="Make it visible to other server members",
    )
    @app_commands.guild_only()
    async def add(self, interaction: discord.Interaction, name: str, source_url: str, public: bool = False):
        await interaction.response.defer(thinking=True)

        source_type = (
            "spotify" if "spotify.com" in source_url else
            "youtube" if ("youtube.com" in source_url or "youtu.be" in source_url) else
            None
        )
        if not source_type:
            await interaction.followup.send("❌ Only YouTube and Spotify URLs are supported.")
            return

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id FROM playlists WHERE owner_id = ? AND name = ?",
                (interaction.user.id, name),
            )
            if await cursor.fetchone():
                await interaction.followup.send(f"❌ You already have a playlist named **{name}**!")
                return
            await db.execute(
                "INSERT INTO playlists (name, owner_id, is_public, source_url, source_type) VALUES (?, ?, ?, ?, ?)",
                (name, interaction.user.id, public, source_url, source_type),
            )
            await db.commit()
            cursor = await db.execute("SELECT last_insert_rowid()")
            playlist_id = (await cursor.fetchone())[0]

        progress_embed = build_progress_embed(
            playlist_name=name, added=0, total=None, last_title=None
        )
        progress_msg = await interaction.followup.send(
            content=f"📋 Playlist **{name}** created (ID `{playlist_id}`). Syncing in the background...",
            embed=progress_embed,
        )

        asyncio.create_task(sync_playlist_background(
            playlist_id=playlist_id,
            playlist_name=name,
            source_url=source_url,
            source_type=source_type,
            progress_message=progress_msg,
            user=interaction.user,
        ))

    @app_commands.command(name="sync", description="Re-sync a playlist from its source URL")
    @app_commands.describe(playlist_id="ID of the playlist to sync")
    @app_commands.guild_only()
    async def sync(self, interaction: discord.Interaction, playlist_id: int):
        await interaction.response.defer(thinking=True)

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name, owner_id, source_url, source_type FROM playlists WHERE id = ?", (playlist_id,)
            )
            row = await cursor.fetchone()

        if not row:
            await interaction.followup.send("❌ Playlist not found!")
            return
        name, owner_id, source_url, source_type = row
        if owner_id != interaction.user.id:
            await interaction.followup.send("❌ You don't own that playlist!")
            return
        if not source_url:
            await interaction.followup.send("❌ No source URL set for this playlist.")
            return

        progress_embed = build_progress_embed(
            playlist_name=name, added=0, total=None, last_title=None
        )
        progress_msg = await interaction.followup.send(
            content=f"🔄 Syncing **{name}** in the background...",
            embed=progress_embed,
        )

        asyncio.create_task(sync_playlist_background(
            playlist_id=playlist_id,
            playlist_name=name,
            source_url=source_url,
            source_type=source_type,
            progress_message=progress_msg,
            user=interaction.user,
        ))

    @app_commands.command(name="remove", description="Delete a playlist and all its songs")
    @app_commands.describe(playlist_id="ID of the playlist to delete")
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, playlist_id: int):
        await interaction.response.defer(thinking=True)

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT owner_id FROM playlists WHERE id = ?", (playlist_id,))
            row = await cursor.fetchone()
            if not row:
                await interaction.followup.send("❌ Playlist not found!")
                return
            if row[0] != interaction.user.id:
                await interaction.followup.send("❌ You can only delete your own playlists!")
                return
            await db.execute("DELETE FROM songs WHERE playlist_id = ?", (playlist_id,))
            await db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            await db.commit()

        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        if player.playlist_id == playlist_id:
            if player.voice_client and player.voice_client.is_playing():
                player.voice_client.stop()
            self.players[guild_id] = PlayerState()

        await interaction.followup.send(f"✅ Playlist `{playlist_id}` deleted.")

    @app_commands.command(name="libraries", description="Browse your playlists or public ones")
    @app_commands.describe(public="Show public playlists from other users")
    @app_commands.guild_only()
    async def libraries(self, interaction: discord.Interaction, public: bool = False):
        await interaction.response.defer(thinking=True)

        async with aiosqlite.connect(DB_PATH) as db:
            if public:
                cursor = await db.execute("""
                    SELECT p.id, p.name, p.owner_id, p.source_type, COUNT(s.id)
                    FROM playlists p LEFT JOIN songs s ON p.id = s.playlist_id
                    WHERE p.is_public = 1
                    GROUP BY p.id HAVING COUNT(s.id) > 0 ORDER BY p.name
                """)
                title = "🌐 Public Playlists"
            else:
                cursor = await db.execute("""
                    SELECT p.id, p.name, p.is_public, p.source_type, COUNT(s.id)
                    FROM playlists p LEFT JOIN songs s ON p.id = s.playlist_id
                    WHERE p.owner_id = ?
                    GROUP BY p.id ORDER BY p.created_at DESC
                """, (interaction.user.id,))
                title = f"📻 {interaction.user.display_name}'s Playlists"

            rows = await cursor.fetchall()

        if not rows:
            await interaction.followup.send("No playlists found." if public else "You have no playlists yet. Use `/radio add` to create one.")
            return

        embed = discord.Embed(title=title, color=discord.Color.blue())
        for row in rows:
            pid, name, vis_or_owner, source_type, cnt = row
            visibility = ("🌐 Public" if vis_or_owner else "🔒 Private") if not public else "🌐 Public"
            source = f"📡 {source_type.upper()}" if source_type else "📝 Manual"
            embed.add_field(name=f"`{pid}` • {name}", value=f"{visibility} • {source} • {cnt} songs", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="songs", description="View songs in a playlist")
    @app_commands.describe(playlist_id="Playlist ID to inspect")
    @app_commands.guild_only()
    async def songs(self, interaction: discord.Interaction, playlist_id: int):
        await interaction.response.defer()

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT name FROM playlists WHERE id = ?", (playlist_id,))
            row = await cursor.fetchone()
            if not row:
                await interaction.followup.send("❌ Playlist not found!")
                return
            playlist_name = row[0]

            cursor = await db.execute(
                "SELECT title, artist, duration FROM songs WHERE playlist_id = ? ORDER BY added_at",
                (playlist_id,),
            )
            song_rows = await cursor.fetchall()

        if not song_rows:
            await interaction.followup.send("📭 This playlist has no songs yet.")
            return

        view = SongsPaginator(song_rows, playlist_name, interaction.user.id)
        await interaction.followup.send(embed=view.build_embed(), view=view)


async def setup(bot: commands.Bot):
    bot.tree.add_command(RadioCommands())
