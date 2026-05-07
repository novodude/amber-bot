import yt_dlp
import asyncio
import aiosqlite
import os
import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

DB_PATH = "data/radio.db"
MAX_SONGS_PER_PLAYLIST = 1500
UPDATE_EVERY = 5
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'skip_download': True,
}


# ── Progress embed ────────────────────────────────────────────────────────────

def build_progress_embed(
    playlist_name: str,
    added: int,
    total: int | None,
    last_title: str | None,
    done: bool = False,
    error: str | None = None,
) -> discord.Embed:
    if error:
        return discord.Embed(
            title="❌ Sync Failed",
            description=error,
            color=discord.Color.red(),
        )

    if done:
        embed = discord.Embed(
            title="✅ Sync Complete",
            description=f"**{playlist_name}** is ready to play!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Songs Added", value=str(added), inline=True)
        return embed

    if total and total > 0:
        filled = int((added / total) * 20)
        bar = "█" * filled + "░" * (20 - filled)
        progress_text = f"`{bar}` {added}/{total}"
    else:
        bar = "█" * min(added, 20)
        progress_text = f"`{bar}` {added} added"

    embed = discord.Embed(
        title=f"🔄 Syncing — {playlist_name}",
        description=progress_text,
        color=discord.Color.blurple(),
    )
    if last_title:
        embed.add_field(name="Last added", value=last_title, inline=False)
    embed.set_footer(text="Running in the background — you can keep using the bot")
    return embed


# ── DB helpers ────────────────────────────────────────────────────────────────

async def song_exists(db, playlist_id: int, file_hash: str) -> bool:
    async with db.execute(
        "SELECT 1 FROM songs WHERE playlist_id = ? AND file_hash = ?",
        (playlist_id, file_hash),
    ) as cursor:
        return await cursor.fetchone() is not None


async def count_playlist_songs(db, playlist_id: int) -> int:
    async with db.execute(
        "SELECT COUNT(*) FROM songs WHERE playlist_id = ?",
        (playlist_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] or 0


async def insert_song(
    db,
    playlist_id: int,
    title: str,
    artist: str | None,
    duration: int,
    file_hash: str,
    stream_url: str,
):
    await db.execute(
        """
        INSERT INTO songs (playlist_id, title, artist, stream_url, duration, file_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (playlist_id, title, artist, stream_url, duration, file_hash),
    )


# ── Core extractor ────────────────────────────────────────────────────────────

async def _extract_entries_from_youtube(url: str) -> list[dict]:
    """Pull all video entries from a YouTube URL without downloading."""
    def sync():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return []
            return info.get("entries", [info])

    return await asyncio.get_event_loop().run_in_executor(None, sync)


# ── Background sync task ──────────────────────────────────────────────────────

async def sync_playlist_background(
    *,
    playlist_id: int,
    playlist_name: str,
    source_url: str,
    source_type: str,
    progress_message: discord.Message,
    user: discord.User,
):
    """
    Runs in the background as an asyncio task.
    Edits progress_message every UPDATE_EVERY songs.
    DMs the user when done.
    """
    added_titles: list[str] = []
    last_title: str | None = None
    total_count: int | None = None

    async def edit_progress(done=False, error=None):
        try:
            embed = build_progress_embed(
                playlist_name=playlist_name,
                added=len(added_titles),
                total=total_count,
                last_title=last_title,
                done=done,
                error=error,
            )
            await progress_message.edit(embed=embed)
        except Exception:
            pass

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            current_count = await count_playlist_songs(db, playlist_id)

        if source_type == "youtube":
            entries = await _extract_entries_from_youtube(source_url)
        elif source_type == "spotify":
            entries = await _resolve_spotify_to_entries(source_url)
        else:
            await edit_progress(error=f"Unknown source type: {source_type}")
            return

        if not entries:
            await edit_progress(error="No tracks found at that URL.")
            return

        total_count = len(entries)
        await edit_progress()  # show 0/total right away

        async with aiosqlite.connect(DB_PATH) as db:
            for v in entries:
                if not v:
                    continue
                if current_count >= MAX_SONGS_PER_PLAYLIST:
                    break

                video_id = v.get("id")
                if not video_id:
                    continue
                if await song_exists(db, playlist_id, video_id):
                    continue

                title = v.get("title", "Unknown Title")
                stream_url = f"https://www.youtube.com/watch?v={video_id}"

                await insert_song(
                    db,
                    playlist_id,
                    title,
                    v.get("uploader"),
                    v.get("duration", 0),
                    video_id,
                    stream_url,
                )
                await db.commit()

                added_titles.append(title)
                last_title = title
                current_count += 1

                if len(added_titles) % UPDATE_EVERY == 0:
                    await edit_progress()

            await db.execute(
                "UPDATE playlists SET last_synced = CURRENT_TIMESTAMP WHERE id = ?",
                (playlist_id,),
            )
            await db.commit()

        await edit_progress(done=True)

        # DM the user when complete
        try:
            dm_embed = discord.Embed(
                title="✅ Sync Complete!",
                description=f"**{playlist_name}** finished syncing.",
                color=discord.Color.green(),
            )
            dm_embed.add_field(name="Songs Added", value=str(len(added_titles)), inline=True)
            if current_count >= MAX_SONGS_PER_PLAYLIST:
                dm_embed.add_field(
                    name="⚠️ Limit Reached",
                    value=f"Stopped at {MAX_SONGS_PER_PLAYLIST} songs.",
                    inline=False,
                )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # DMs closed, no big deal

    except Exception as e:
        await edit_progress(error=str(e))


# ── Spotify resolver ──────────────────────────────────────────────────────────

async def _resolve_spotify_to_entries(url: str) -> list[dict]:
    """Resolve Spotify tracks → YouTube search results → entry dicts."""
    def get_tracks():
        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
            )
        )
        if "playlist" in url:
            return [item["track"] for item in sp.playlist_items(url)["items"] if item.get("track")]
        elif "track" in url:
            return [sp.track(url)]
        return []

    tracks = await asyncio.get_event_loop().run_in_executor(None, get_tracks)
    entries = []
    for track in tracks:
        query = f"ytsearch1:{track['name']} {track['artists'][0]['name']} audio"
        results = await _extract_entries_from_youtube(query)
        if results:
            entries.append(results[0])
    return entries


# ── Immediate stream URL resolver ─────────────────────────────────────────────

async def resolve_stream_url(youtube_watch_url: str) -> str | None:
    """
    Resolve a youtube.com/watch?v=... URL to a real audio stream URL
    for immediate FFmpeg playback.
    """
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    def sync():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_watch_url, download=False)
            if not info:
                return None
            return info.get("url") or (info.get("formats") or [{}])[-1].get("url")

    return await asyncio.get_event_loop().run_in_executor(None, sync)
