import asyncio
import random
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from utils.radio.audio_processor import (
    sync_playlist_background,
    resolve_stream_url,
    build_progress_embed,
)
from utils.radio.database import (
    add_song_to_favorites,
    remove_song_from_favorites,
    get_accessible_playlists,
    get_user_playlists,
    get_playlist,
    get_playlist_for_sync,
    get_user_libraries,
    get_public_libraries,
    playlist_name_exists,
    create_playlist,
    delete_playlist,
    get_playlist_songs,
    get_playlist_songs_display,
    get_playlist_songs_with_ids,
    get_mix_songs,
    add_song_to_playlist,
    set_playlist_privacy,
    delete_song,
)

FFMPEG_STREAM_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -vn"
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
        self._toggle: bool = False


# ── Search result paginator ────────────────────────────────────────────────────

class SearchResultsView(discord.ui.View):
    """One result per page. from_player=True adds Play Now + Play Next + Add to Queue buttons."""

    def __init__(
        self,
        results: list[dict],
        user_id: int,
        radio_cog: "RadioCommands",
        guild_id: int | None,
        from_player: bool = False,
    ):
        super().__init__(timeout=120)
        self.results = results
        self.user_id = user_id
        self.radio_cog = radio_cog
        self.guild_id = guild_id
        self.from_player = from_player
        self.page = 0
        self._rebuild_buttons()

    def _current(self) -> dict:
        return self.results[self.page]

    def build_embed(self) -> discord.Embed:
        r = self._current()
        mins, secs = divmod(int(r.get("duration") or 0), 60)
        embed = discord.Embed(
            title=r["title"],
            url=r["url"],
            color=discord.Color.blurple(),
        )
        embed.set_author(name=f"🔍 Search Results — {self.page + 1}/{len(self.results)}")
        embed.add_field(name="Channel", value=r.get("uploader") or "Unknown", inline=True)
        embed.add_field(name="Duration", value=f"{mins}:{secs:02d}", inline=True)
        if r.get("thumbnail"):
            embed.set_thumbnail(url=r["thumbnail"])
        return embed

    def _rebuild_buttons(self):
        self.clear_items()

        prev = discord.ui.Button(
            label="⬅ Prev", style=discord.ButtonStyle.secondary,
            disabled=self.page == 0, row=0,
        )
        prev.callback = self._prev
        self.add_item(prev)

        next_ = discord.ui.Button(
            label="Next ➡", style=discord.ButtonStyle.secondary,
            disabled=self.page >= len(self.results) - 1, row=0,
        )
        next_.callback = self._next
        self.add_item(next_)

        like_btn = discord.ui.Button(emoji="🤍", style=discord.ButtonStyle.secondary, row=1)
        like_btn.callback = self._like
        self.add_item(like_btn)

        add_btn = discord.ui.Button(label="➕ Add to Playlist", style=discord.ButtonStyle.primary, row=1)
        add_btn.callback = self._show_playlist_select
        self.add_item(add_btn)

        if self.from_player:
            play_now_btn = discord.ui.Button(label="▶️ Play Now", style=discord.ButtonStyle.success, row=1)
            play_now_btn.callback = self._play_now
            self.add_item(play_now_btn)

            play_next_btn = discord.ui.Button(label="⏭️ Play Next", style=discord.ButtonStyle.success, row=1)
            play_next_btn.callback = self._play_next
            self.add_item(play_next_btn)

            queue_btn = discord.ui.Button(label="📋 Add to Queue", style=discord.ButtonStyle.secondary, row=1)
            queue_btn.callback = self._add_to_queue
            self.add_item(queue_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your search results!", ephemeral=True)
            return False
        return True

    async def _prev(self, interaction: discord.Interaction):
        self.page = max(self.page - 1, 0)
        self._rebuild_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _next(self, interaction: discord.Interaction):
        self.page = min(self.page + 1, len(self.results) - 1)
        self._rebuild_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _like(self, interaction: discord.Interaction):
        r = self._current()
        added = await add_song_to_favorites(
            interaction.user,
            r["title"],
            r.get("uploader") or "Unknown",
            r["url"],
            r.get("duration") or 0,
        )
        if added:
            await interaction.response.send_message(f"🤍 **{r['title']}** added to your liked songs!", ephemeral=True)
        else:
            await remove_song_from_favorites(interaction.user, r["url"])
            await interaction.response.send_message(f"🖤 **{r['title']}** removed from your liked songs!", ephemeral=True)

    async def _show_playlist_select(self, interaction: discord.Interaction):
        playlists = await get_user_playlists(interaction.user.id)

        options = [
            discord.SelectOption(label="➕ Create new playlist...", value="__create__"),
            *[
                discord.SelectOption(label=name[:100], value=str(pid))
                for pid, name in playlists
            ]
        ]

        select = discord.ui.Select(placeholder="Choose a playlist...", options=options)
        r = self._current()

        async def _on_select(inner: discord.Interaction):
            if select.values[0] == "__create__":
                modal = discord.ui.Modal(title="Create Playlist")
                name_input = discord.ui.TextInput(label="Playlist name", placeholder="My awesome playlist", min_length=1, max_length=100)
                public_input = discord.ui.TextInput(label="Public? (yes / no)", placeholder="no", min_length=2, max_length=3)
                modal.add_item(name_input)
                modal.add_item(public_input)

                async def on_modal_submit(modal_interaction: discord.Interaction):
                    name = name_input.value.strip()
                    is_public = public_input.value.strip().lower() in ("yes", "y")
                    if await playlist_name_exists(modal_interaction.user.id, name):
                        await modal_interaction.response.send_message(f"❌ You already have a playlist named **{name}**!", ephemeral=True)
                        return
                    new_pid = await create_playlist(modal_interaction.user.id, name, is_public, None, None)
                    await add_song_to_playlist(new_pid, r["title"], r.get("uploader") or "Unknown", r["url"], r.get("duration") or 0)
                    visibility = "🌐 public" if is_public else "🔒 private"
                    await modal_interaction.response.send_message(
                        f"✅ Playlist **{name}** created ({visibility}) and **{r['title']}** added to it!", ephemeral=True
                    )

                modal.on_submit = on_modal_submit
                await inner.response.send_modal(modal)
                return

            pid = int(select.values[0])
            inserted = await add_song_to_playlist(pid, r["title"], r.get("uploader") or "Unknown", r["url"], r.get("duration") or 0)
            playlist_name = next(name for pid2, name in playlists if pid2 == pid)
            if inserted:
                await inner.response.send_message(f"➕ **{r['title']}** added to **{playlist_name}**!", ephemeral=True)
            else:
                await inner.response.send_message(f"**{r['title']}** is already in **{playlist_name}**.", ephemeral=True)

        select.callback = _on_select
        tmp_view = discord.ui.View(timeout=60)
        tmp_view.add_item(select)
        await interaction.response.send_message(view=tmp_view, ephemeral=True)

    async def _play_now(self, interaction: discord.Interaction):
        if not self.guild_id:
            await interaction.response.send_message("No active guild.", ephemeral=True)
            return
        player = self.radio_cog._get_player(self.guild_id)
        if not player.voice_client or not player.voice_client.is_connected():
            await interaction.response.send_message("❌ I'm not in a voice channel. Use `/radio play` first to connect me.", ephemeral=True)
            return
        r = self._current()
        song = (None, r["title"], r.get("uploader"), r["url"], int(r.get("duration") or 0))
        player.songs.insert(player.current_index + 1, song)
        if player.voice_client.is_playing() or player.voice_client.is_paused():
            player.current_index += 1
            player.voice_client.stop()
            await interaction.response.send_message(f"▶️ Playing **{r['title']}** now!", ephemeral=True)
        else:
            player.playlist_name = r["title"]
            await self.radio_cog._play_current(self.guild_id)
            await interaction.response.send_message(f"▶️ Playing **{r['title']}**!", ephemeral=True)
        await self.radio_cog._update_message(self.guild_id)

    async def _play_next(self, interaction: discord.Interaction):
        if not self.guild_id:
            await interaction.response.send_message("No active guild.", ephemeral=True)
            return
        player = self.radio_cog._get_player(self.guild_id)
        if not player.voice_client or not player.songs:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
            return
        r = self._current()
        player.songs.insert(player.current_index + 1, (None, r["title"], r.get("uploader"), r["url"], r.get("duration") or 0))
        await interaction.response.send_message(f"⏭️ **{r['title']}** will play next!", ephemeral=True)
        await self.radio_cog._update_message(self.guild_id)

    async def _add_to_queue(self, interaction: discord.Interaction):
        if not self.guild_id:
            await interaction.response.send_message("No active guild.", ephemeral=True)
            return
        player = self.radio_cog._get_player(self.guild_id)
        if not player.voice_client or not player.songs:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
            return
        r = self._current()
        player.songs.append((None, r["title"], r.get("uploader"), r["url"], r.get("duration") or 0))
        await interaction.response.send_message(f"📋 **{r['title']}** added to queue (position {len(player.songs)})!", ephemeral=True)
        await self.radio_cog._update_message(self.guild_id)


# ── Song paginator ─────────────────────────────────────────────────────────────

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
            mins, secs = divmod(int(duration or 0), 60)
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


# ── Radio commands ─────────────────────────────────────────────────────────────

class RadioCommands(app_commands.Group):
    """All radio commands. Audio is streamed directly."""

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
            mins, secs = divmod(int(duration or 0), 60)
            embed.description = f"**{title}**\nby {artist or 'Unknown'}"
            embed.add_field(name="Playlist", value=player.playlist_name, inline=True)
            embed.add_field(name="Track", value=f"{player.current_index + 1}/{len(player.songs)}", inline=True)
            embed.add_field(name="Duration", value=f"{mins}:{secs:02d}", inline=True)
        else:
            embed.description = "**Nothing playing** — use the 🔍 button to search for a song, or pick a playlist from the dropdown above."
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

        playlists = await get_accessible_playlists(user_id)
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

        view.add_item(_make_btn("⏮️", discord.ButtonStyle.secondary, f"radio_back_{guild_id}",    self._btn_back,      1))
        view.add_item(_make_btn("⏸️", discord.ButtonStyle.primary,   f"radio_play_{guild_id}",    self._btn_playpause, 1))
        view.add_item(_make_btn("⏭️", discord.ButtonStyle.secondary, f"radio_next_{guild_id}",    self._btn_next,      1))
        view.add_item(_make_btn("🤍", discord.ButtonStyle.secondary, f"radio_like_{guild_id}",    self._btn_like,      1))
        view.add_item(_make_btn("🔉", discord.ButtonStyle.secondary, f"radio_vold_{guild_id}",    self._btn_vol_down,  2))
        view.add_item(_make_btn("🔁", discord.ButtonStyle.secondary, f"radio_loop_{guild_id}",    self._btn_loop,      2))
        view.add_item(_make_btn("🔊", discord.ButtonStyle.secondary, f"radio_volu_{guild_id}",    self._btn_vol_up,    2))
        view.add_item(_make_btn("⏹️", discord.ButtonStyle.danger,    f"radio_stop_{guild_id}",    self._btn_stop,      2))
        view.add_item(_make_btn("🔍", discord.ButtonStyle.secondary, f"radio_search_{guild_id}",  self._btn_search,    3))
        view.add_item(_make_btn("🔀", discord.ButtonStyle.secondary, f"radio_shuffle_{guild_id}", self._btn_shuffle,   3))

        return view

    async def _keepalive_loop(self, guild_id: int):
        while True:
            await asyncio.sleep(300)
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

        stream_url = await resolve_stream_url(watch_url)
        if not stream_url:
            player.current_index += 1
            await self._play_current(guild_id)
            return

        event_loop = asyncio.get_event_loop()

        def after_playing(error):
            if error:
                print(f"[radio] playback error: {error}")
            asyncio.run_coroutine_threadsafe(self._advance(guild_id), event_loop)

        src = discord.FFmpegPCMAudio(stream_url, before_options=FFMPEG_STREAM_OPTIONS)
        source = discord.PCMVolumeTransformer(src, volume=player.volume)
        player.voice_client.play(source, after=after_playing)

        if not getattr(player, '_keepalive_task', None) or player._keepalive_task.done():
            player._keepalive_task = asyncio.create_task(self._keepalive_loop(guild_id))

        await self._update_message(guild_id)

    async def _advance(self, guild_id: int):
        player = self._get_player(guild_id)
        if player.loop_song:
            await self._play_current(guild_id)
            return
        if player.current_index + 1 >= len(player.songs):
            player.current_index = 0 if player.loop else len(player.songs)
        else:
            player.current_index += 1
        await self._play_current(guild_id)

    async def _update_message(self, guild_id: int, interaction: discord.Interaction | None = None):
        player = self._get_player(guild_id)
        if not player.message:
            return
        try:
            player._toggle = not player._toggle
            content = "** **" if player._toggle else "**  **"
            embed = self._create_embed(player)
            view = await self._create_view(guild_id, player.user_id)

            # If triggered by a button, use the active interaction to respond safely
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(content=content, embed=embed, view=view)
            else:
                # Fallback if called by an automated background task
                await player.message.edit(content=content, embed=embed, view=view)
        except Exception as e:
            print(f"[radio] _update_message failed: {e}")

    async def _ensure_voice(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice:
            await interaction.followup.send("❌ Join a voice channel first!", ephemeral=True)
            return False
        return True

    async def _send_songs_paginator(self, interaction: discord.Interaction, playlist_id: int):
        row = await get_playlist(playlist_id)
        if not row:
            await interaction.followup.send("❌ Playlist not found!")
            return
        playlist_name = row[0]
        song_rows = await get_playlist_songs_display(playlist_id)
        if not song_rows:
            await interaction.followup.send("📭 This playlist has no songs yet.")
            return
        view = SongsPaginator(song_rows, playlist_name, interaction.user.id)
        await interaction.followup.send(embed=view.build_embed(), view=view)

    async def _pick_playlist(
        self,
        interaction: discord.Interaction,
        prompt: str,
        then: callable,
    ):
        """Show a playlist dropdown and call `then(interaction, playlist_id)` on selection."""
        playlists = await get_user_playlists(interaction.user.id, limit=25)
        if not playlists:
            await interaction.followup.send("You have no playlists yet. Use `/radio add` to create one.")
            return

        options = [
            discord.SelectOption(label=name[:100], value=str(pid))
            for pid, name in playlists
        ]
        select = discord.ui.Select(placeholder="Choose a playlist...", options=options)

        async def _on_select(inner: discord.Interaction):
            await inner.response.defer()
            await then(inner, int(select.values[0]))

        select.callback = _on_select
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        await interaction.followup.send(prompt, view=view, ephemeral=True)

    @staticmethod
    async def _yt_search(query: str, max_results: int = 10) -> list[dict]:
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": True,
        }

        def sync():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                return info.get("entries", [])

        entries = await asyncio.get_event_loop().run_in_executor(None, sync)
        results = []
        for e in entries:
            if not e:
                continue
            vid_id = e.get("id") or e.get("url", "")
            results.append({
                "title": e.get("title") or "Unknown",
                "uploader": e.get("uploader") or e.get("channel") or "Unknown",
                "duration": e.get("duration") or 0,
                "url": f"https://www.youtube.com/watch?v={vid_id}" if len(vid_id) == 11 else e.get("url", ""),
                "thumbnail": e.get("thumbnail"),
            })
        return results

    # ── Button callbacks ───────────────────────────────────────────────────────

    async def _select_playlist_callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        player = self._get_player(guild_id)
        playlist_id = int(interaction.data["values"][0])

        row = await get_playlist(playlist_id)
        if not row:
            await interaction.response.send_message("Playlist not found!", ephemeral=True)
            return
        name, owner_id, is_public = row
        if owner_id != interaction.user.id and not is_public:
            await interaction.response.send_message("That playlist is private!", ephemeral=True)
            return

        songs = await get_playlist_songs(playlist_id)
        if not songs:
            await interaction.response.send_message("That playlist has no songs!", ephemeral=True)
            return

        player.playlist_id = playlist_id
        player.playlist_name = name
        player.songs = songs
        player.current_index = 0

        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
            await asyncio.sleep(0.5)

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

        await self._update_message(interaction.guild_id, interaction=interaction)

    async def _btn_vol_up(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        player.volume = min(1.0, player.volume + 0.1)
        if player.voice_client and player.voice_client.source:
            player.voice_client.source.volume = player.volume

        await self._update_message(interaction.guild_id, interaction=interaction)

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

    async def _btn_like(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if not player.songs or player.current_index >= len(player.songs):
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        _, title, artist, stream_url, duration = player.songs[player.current_index]
        added = await add_song_to_favorites(interaction.user, title, artist or "Unknown", stream_url, duration or 0)
        if added:
            await interaction.response.send_message(f"🤍 **{title}** added to your liked songs!", ephemeral=True)
        else:
            await remove_song_from_favorites(interaction.user, stream_url)
            await interaction.response.send_message(f"🖤 **{title}** removed from your liked songs!", ephemeral=True)

    async def _btn_shuffle(self, interaction: discord.Interaction):
        player = self._get_player(interaction.guild_id)
        if not player.songs:
            await interaction.response.send_message("Nothing to shuffle.", ephemeral=True)
            return
        current_song = player.songs[player.current_index]
        rest = [s for i, s in enumerate(player.songs) if i != player.current_index]
        random.shuffle(rest)
        player.songs = [current_song] + rest
        player.current_index = 0
        await self._update_message(interaction.guild_id)
        await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)

    async def _btn_search(self, interaction: discord.Interaction):
        modal = discord.ui.Modal(title="Search YouTube")
        query_input = discord.ui.TextInput(
            label="Search query",
            placeholder="e.g. lofi hip hop chill beats",
            min_length=1,
            max_length=100,
        )
        modal.add_item(query_input)

        async def on_submit(modal_interaction: discord.Interaction):
            await modal_interaction.response.defer(ephemeral=True, thinking=True)
            results = await self._yt_search(query_input.value)
            if not results:
                await modal_interaction.followup.send("❌ No results found.", ephemeral=True)
                return
            view = SearchResultsView(
                results=results,
                user_id=interaction.user.id,
                radio_cog=self,
                guild_id=interaction.guild_id,
                from_player=True,
            )
            await modal_interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

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

        if mix_mode:
            player.songs = await get_mix_songs(interaction.user.id)
            if not player.songs:
                await interaction.followup.send("❌ No songs available for mix mode!")
                return
            player.playlist_name = "🎲 Mix Mode"
            player.current_index = 0
            embed = self._create_embed(player)
            view = await self._create_view(guild_id, interaction.user.id)
            
            await interaction.followup.send("▶️ Starting Mix Mode...", ephemeral=True)
            
            player.message = await interaction.channel.send(content="** **", embed=embed, view=view)
            
            await self._play_current(guild_id)
            return

        if not playlist_id:
            embed = self._create_embed(player)
            view = await self._create_view(guild_id, interaction.user.id)
            
            await interaction.followup.send("Have fun!")
            
            player.message = await interaction.channel.send(content="** **", embed=embed, view=view)
            return

        row = await get_playlist(playlist_id)
        if not row:
            await interaction.followup.send("❌ Playlist not found!")
            return
        name, owner_id, is_public = row
        if owner_id != interaction.user.id and not is_public:
            await interaction.followup.send("❌ That playlist is private!")
            return

        player.songs = await get_playlist_songs(playlist_id)
        if not player.songs:
            await interaction.followup.send("❌ That playlist has no songs!")
            return

        player.playlist_id = playlist_id
        player.playlist_name = name
        player.current_index = 0

        embed = self._create_embed(player)
        view = await self._create_view(guild_id, interaction.user.id)
        
        await interaction.followup.send(f"▶️ Starting **{name}**...")
        
        player.message = await interaction.channel.send(content="** **", embed=embed, view=view)
        
        await self._play_current(guild_id)

    @app_commands.command(name="search", description="Search YouTube and add songs to your library")
    @app_commands.describe(query="What to search for")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        results = await self._yt_search(query)
        if not results:
            await interaction.followup.send("❌ No results found.", ephemeral=True)
            return
        view = SearchResultsView(
            results=results,
            user_id=interaction.user.id,
            radio_cog=self,
            guild_id=interaction.guild_id,
            from_player=False,
        )
        await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)

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

        def sync():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(source_url, download=False)

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
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
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

        if await playlist_name_exists(interaction.user.id, name):
            await interaction.followup.send(f"❌ You already have a playlist named **{name}**!")
            return

        playlist_id = await create_playlist(interaction.user.id, name, public, source_url, source_type)

        progress_embed = build_progress_embed(playlist_name=name, added=0, total=None, last_title=None)
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
    @app_commands.describe(playlist_id="Playlist ID to sync (leave empty to pick from a dropdown)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def sync(self, interaction: discord.Interaction, playlist_id: int | None = None):
        await interaction.response.defer(thinking=True)

        async def _do_sync(inner: discord.Interaction, pid: int):
            row = await get_playlist_for_sync(pid)
            if not row:
                await inner.followup.send("❌ Playlist not found!")
                return
            name, owner_id, source_url, source_type = row
            if owner_id != inner.user.id:
                await inner.followup.send("❌ You don't own that playlist!")
                return
            if not source_url:
                await inner.followup.send("❌ No source URL set for this playlist.")
                return
            progress_embed = build_progress_embed(playlist_name=name, added=0, total=None, last_title=None)
            progress_msg = await inner.followup.send(
                content=f"🔄 Syncing **{name}** in the background...", embed=progress_embed
            )
            asyncio.create_task(sync_playlist_background(
                playlist_id=pid, playlist_name=name, source_url=source_url,
                source_type=source_type, progress_message=progress_msg, user=inner.user,
            ))

        if not playlist_id:
            await self._pick_playlist(interaction, "Which playlist do you want to sync?", _do_sync)
            return
        await _do_sync(interaction, playlist_id)

    @app_commands.command(name="remove", description="Delete a playlist and all its songs")
    @app_commands.describe(playlist_id="Playlist ID to delete (leave empty to pick from a dropdown)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def remove(self, interaction: discord.Interaction, playlist_id: int | None = None):
        await interaction.response.defer(thinking=True)

        async def _do_remove(inner: discord.Interaction, pid: int):
            row = await get_playlist(pid)
            if not row:
                await inner.followup.send("❌ Playlist not found!")
                return
            name, owner_id, is_public = row
            if owner_id != inner.user.id:
                await inner.followup.send("❌ You can only delete your own playlists!")
                return
            await delete_playlist(pid)
            guild_id = inner.guild_id
            if guild_id:
                player = self._get_player(guild_id)
                if player.playlist_id == pid:
                    if player.voice_client and player.voice_client.is_playing():
                        player.voice_client.stop()
                    self.players[guild_id] = PlayerState()
            await inner.followup.send(f"✅ Playlist **{name}** deleted.")

        if not playlist_id:
            await self._pick_playlist(interaction, "Which playlist do you want to delete?", _do_remove)
            return
        await _do_remove(interaction, playlist_id)

    @app_commands.command(name="privacy", description="Toggle a playlist between public and private")
    @app_commands.describe(playlist_id="Playlist ID to update (leave empty to pick from a dropdown)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def privacy(self, interaction: discord.Interaction, playlist_id: int | None = None):
        await interaction.response.defer(thinking=True)

        async def _do_privacy(inner: discord.Interaction, pid: int):
            row = await get_playlist(pid)
            if not row:
                await inner.followup.send("❌ Playlist not found!")
                return
            name, owner_id, is_public = row
            if owner_id != inner.user.id:
                await inner.followup.send("❌ You can only edit your own playlists!")
                return
            new_state = not is_public
            await set_playlist_privacy(pid, new_state)
            visibility = "🌐 public" if new_state else "🔒 private"
            await inner.followup.send(f"✅ **{name}** is now {visibility}.")

        if not playlist_id:
            await self._pick_playlist(interaction, "Which playlist do you want to update?", _do_privacy)
            return
        await _do_privacy(interaction, playlist_id)

    @app_commands.command(name="remove-song", description="Remove a song from one of your playlists")
    @app_commands.describe(playlist_id="Playlist ID (leave empty to pick from a dropdown)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def remove_song(self, interaction: discord.Interaction, playlist_id: int | None = None):
        await interaction.response.defer(thinking=True)

        async def _do_remove_song(inner: discord.Interaction, pid: int):
            row = await get_playlist(pid)
            if not row:
                await inner.followup.send("❌ Playlist not found!")
                return
            name, owner_id, _ = row
            if owner_id != inner.user.id:
                await inner.followup.send("❌ You can only edit your own playlists!")
                return

            songs = await get_playlist_songs_with_ids(pid)
            if not songs:
                await inner.followup.send("📭 That playlist has no songs.")
                return

            # paginate into groups of 25 for the dropdown
            page = 0
            per_page = 25

            def _build_select(p: int) -> discord.ui.Select:
                start = p * per_page
                chunk = songs[start:start + per_page]
                options = [
                    discord.SelectOption(
                        label=title[:100],
                        value=str(sid),
                        description=f"{artist or 'Unknown'}"[:100],
                    )
                    for sid, title, artist, duration in chunk
                ]
                return discord.ui.Select(placeholder=f"Choose a song to remove... (page {p + 1})", options=options)

            def _build_view(p: int) -> discord.ui.View:
                v = discord.ui.View(timeout=60)
                select = _build_select(p)

                async def _on_song_select(song_interaction: discord.Interaction):
                    sid = int(select.values[0])
                    song_title = next(title for s_id, title, _, _ in songs if s_id == sid)
                    await delete_song(sid)
                    await song_interaction.response.edit_message(
                        content=f"✅ **{song_title}** removed from **{name}**.", view=None
                    )

                select.callback = _on_song_select
                v.add_item(select)

                max_page = (len(songs) - 1) // per_page
                if p > 0:
                    prev_btn = discord.ui.Button(label="⬅ Prev", style=discord.ButtonStyle.secondary)
                    async def _prev(btn_interaction: discord.Interaction):
                        await btn_interaction.response.edit_message(view=_build_view(p - 1))
                    prev_btn.callback = _prev
                    v.add_item(prev_btn)
                if p < max_page:
                    next_btn = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.secondary)
                    async def _next(btn_interaction: discord.Interaction):
                        await btn_interaction.response.edit_message(view=_build_view(p + 1))
                    next_btn.callback = _next
                    v.add_item(next_btn)

                return v

            await inner.followup.send(
                f"Which song do you want to remove from **{name}**?",
                view=_build_view(page),
                ephemeral=True,
            )

        if not playlist_id:
            await self._pick_playlist(interaction, "Which playlist do you want to remove a song from?", _do_remove_song)
            return
        await _do_remove_song(interaction, playlist_id)

    @app_commands.command(name="libraries", description="Browse your playlists or public ones")
    @app_commands.describe(public="Show public playlists from other users")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def libraries(self, interaction: discord.Interaction, public: bool = False):
        await interaction.response.defer(thinking=True)

        if public:
            rows = await get_public_libraries()
            title = "🌐 Public Playlists"
        else:
            rows = await get_user_libraries(interaction.user.id)
            title = f"📻 {interaction.user.display_name}'s Playlists"

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
    @app_commands.describe(playlist_id="Playlist ID to inspect (leave empty to pick from a dropdown)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def songs(self, interaction: discord.Interaction, playlist_id: int | None = None):
        await interaction.response.defer()

        if not playlist_id:
            await self._pick_playlist(interaction, "Which playlist do you want to browse?", self._send_songs_paginator)
            return
        await self._send_songs_paginator(interaction, playlist_id)


async def setup(bot: commands.Bot):
    bot.tree.add_command(RadioCommands())
