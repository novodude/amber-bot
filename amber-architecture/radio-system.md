# Radio System

A local audio player that downloads playlists from YouTube or Spotify and plays them in voice channels.

---

## Overview

Users create playlists by providing a YouTube or Spotify URL. Songs are downloaded as `.opus` files using `yt-dlp` and stored locally under `data/audio/playlist_{id}/`. The radio player streams them into a voice channel using FFmpeg via discord.py's `FFmpegPCMAudio`.

The system is split into two Cogs:
- `commands/radio/player.py` — `RadioPlayer` Cog: playback control, voice connection, button UI
- `commands/radio/settings.py` — `RadioSettings` Cog: playlist management (add, remove, sync, list, songs)

Both are loaded as extensions in `load_extensions()`.

---

## Data Flow

```
/radio_add [name] [url]
  └── detect source type (youtube / spotify)
  └── create row in playlists table
  └── call _sync_playlist()
        └── download_from_youtube() or download_from_spotify()
              └── yt-dlp downloads → TEMP_DIR → move to playlist_{id}/
              └── insert song rows into songs table

/radio [playlist_id]
  └── connect to voice channel
  └── load songs from DB
  └── play_current_song()
        └── FFmpegPCMAudio(file_path)
        └── PCMVolumeTransformer(source, volume)
        └── after=advance_to_next callback
```

---

## Storage Layout

```
data/
├── radio.db
└── audio/
    ├── temp/                        ← yt-dlp downloads here first
    │   └── {video_id}.opus
    └── playlist_{id}/               ← moved here on success
        └── {video_id}.opus
```

Song limit: 150 songs per user across all their playlists.

---

## PlayerState

`RadioPlayer.PlayerState` holds all in-memory playback state per guild.

| Attribute | Type | Description |
|---|---|---|
| `playlist_id` | int | Current playlist DB ID |
| `playlist_name` | str | Display name |
| `songs` | list | List of `(id, title, artist, file_path, duration)` tuples |
| `current_index` | int | Current song index |
| `volume` | float | 0.0–1.0, default 0.5 |
| `loop` | bool | Loop playlist (default True) |
| `loop_song` | bool | Loop current song |
| `mix_mode` | bool | All accessible playlists shuffled |
| `voice_client` | VoiceClient | Discord voice connection |
| `message` | WebhookMessage | The player embed message (updated in place) |

One `PlayerState` per guild, stored in `self.players[guild_id]`.

---

## Playback Controls

The player UI is a discord.py `View` with buttons and a playlist dropdown (row 0 = dropdown, rows 1–2 = buttons).

| Button | Action |
|---|---|
| ⏮️ | Previous song (decrements index, stops current) |
| ⏸️ | Pause / Resume toggle |
| ⏭️ | Next song |
| 🔉 | Volume -10% |
| 🔁 | Cycle loop mode: playlist → song → off |
| 🔊 | Volume +10% |
| ⏹️ | Stop and disconnect |

The player embed is edited in place after each interaction — not re-sent.

### After-play callback

When a song ends, `advance_to_next()` is scheduled via `asyncio.run_coroutine_threadsafe()`. This increments `current_index` (or wraps if looping) and calls `play_current_song()` again.

---

## Spotify Support

Spotify downloads work by:
1. Using `spotipy` to fetch track metadata (name + artist).
2. Constructing a `ytsearch1:` query for yt-dlp.
3. Downloading the top YouTube result.

Spotify playlists iterate through all tracks. Requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` env vars.

`/download` with a Spotify URL returns metadata only — it does not download Spotify audio.

---

## Commands Detail

### `/radio_add [name] [url] [public?]`

Creates a playlist record and immediately syncs it. Sends progress embed ("Syncing Playlist...") then edits it to "Sync Complete" or "Sync Failed".

### `/radio_sync [id]`

Owner-only. Re-runs the download pipeline for the playlist's source URL. Deduplicates by `file_hash` (YouTube video ID).

### `/radio_remove [id]`

Owner-only. Deletes the `playlists` row (CASCADE deletes `songs` rows), physically removes `.opus` files from disk, and updates the active player embed if this playlist was playing.

### `/radio_libraries [public?]`

- `public=False` (default): shows your own playlists with visibility and song count.
- `public=True`: shows other users' public playlists.

### `/radio_songs [id]`

Paginated song list using `PlaylistSongsPaginator` — 10 songs per page with back/next buttons.

---

## Audio Processing (`utils/radio/audio_processor.py`)

### `download_from_youtube(url, playlist_id)`

Downloads via yt-dlp with `bestaudio/best` format, converted to Opus at 128k via FFmpeg postprocessor. Handles both single videos and full playlists. Deduplicates using `file_hash = video_id`. Returns `(success, added_titles, message)`.

### `download_from_spotify(url, playlist_id)`

Extracts track metadata via spotipy, then delegates each track to `download_from_youtube` via `ytsearch1:` query. Returns `(success, added_titles, message)`.

### `convert_to_opus(input_path, output_path)`

Standalone FFmpeg conversion function. Used as fallback if yt-dlp postprocessor doesn't produce the right file.

### yt-dlp options

```python
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'outtmpl': f"{TEMP_DIR}/%(id)s.%(ext)s",
    'postprocessors': [
        {'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus', 'preferredquality': '128'}
    ],
}
```
