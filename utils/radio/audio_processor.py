import yt_dlp
import os
import asyncio
import aiosqlite
import hashlib
import subprocess
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

DB_PATH = "data/radio.db"
TEMP_DIR = "data/audio/temp"
MAX_SONGS_PER_USER = 150

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'outtmpl': f"{TEMP_DIR}/%(id)s.%(ext)s",
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '128',
        }
    ],
}


def convert_to_opus(input_path: str, output_path: str):
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-c:a", "libopus", "-b:a", "128k", output_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def song_exists(db, playlist_id, file_hash):
    async with db.execute(
        "SELECT 1 FROM songs WHERE playlist_id = ? AND file_hash = ?",
        (playlist_id, file_hash),
    ) as cursor:
        return await cursor.fetchone() is not None


async def insert_song(db, playlist_id, title, artist, path, duration, file_hash):
    await db.execute(
        """
        INSERT INTO songs (playlist_id, title, artist, file_path, duration, file_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (playlist_id, title, artist, path, duration, file_hash),
    )


async def count_user_songs(db, playlist_id):
    async with db.execute(
        """
        SELECT COUNT(s.id)
        FROM songs s
        JOIN playlists p ON p.id = s.playlist_id
        WHERE p.owner_id = (
            SELECT owner_id FROM playlists WHERE id = ?
        )
        """,
        (playlist_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] or 0


async def download_from_youtube(url: str, playlist_id: int):
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(f"data/audio/playlist_{playlist_id}", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        current_count = await count_user_songs(db, playlist_id)
        if current_count >= MAX_SONGS_PER_USER:
            return False, [], "❌ Song limit reached (150)."

        def sync():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                return ydl.extract_info(url, download=True)

        info = await asyncio.get_event_loop().run_in_executor(None, sync)
        if not info:
            return False, [], "Failed to extract YouTube info."

        entries = info.get("entries", [info])
        added = []

        for v in entries:
            if current_count >= MAX_SONGS_PER_USER:
                break
            if not v:
                continue

            video_id = v["id"]
            temp = f"{TEMP_DIR}/{video_id}.opus"
            final = f"data/audio/playlist_{playlist_id}/{video_id}.opus"

            if await song_exists(db, playlist_id, video_id):
                continue

            if os.path.exists(temp):
                os.rename(temp, final)
                await insert_song(
                    db,
                    playlist_id,
                    v.get("title"),
                    v.get("uploader"),
                    final,
                    v.get("duration", 0),
                    video_id,
                )
                added.append(v.get("title"))
                current_count += 1

        await db.commit()

        if current_count >= MAX_SONGS_PER_USER:
            return True, added, "⚠️ Song limit reached (150). Import stopped."

        return True, added, None


# Spotify client
spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    )
)


async def download_from_spotify(url: str, playlist_id: int):
    tracks = []

    if "playlist" in url:
        tracks = spotify.playlist_items(url)["items"]
    elif "track" in url:
        tracks = [{"track": spotify.track(url)}]
    else:
        return False, [], "Unsupported Spotify URL."

    added = []

    for item in tracks:
        track = item.get("track")
        if not track:
            continue

        # Search YouTube for the track
        query = f"{track['name']} {track['artists'][0]['name']} audio"
        yt_url = f"ytsearch1:{query}"

        ok, songs, msg = await download_from_youtube(yt_url, playlist_id)
        if not ok:
            return False, added, msg

        added.extend(songs)
        if msg:
            break

    return True, added, None
