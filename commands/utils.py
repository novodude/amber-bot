from datetime import datetime
from discord import app_commands
from catbox import CatboxUploader
from typing import Literal, Optional
import shutil
import tempfile
import asyncio
import discord
import spotipy
import yt_dlp
import io
import os
import re

def download_with_ytdlp(video_url, output_path, audio_only=True):
    ydl_opts_audio = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",
        }],
        "max_filesize": 600 * 1024 * 1024,
        "quiet": True,
        "no_warnings": True
    }

    ydl_opts_video = {
        # Caps the video resolution at 480p, then adds best audio. 
        "format": "bestvideo+bestaudio" if not is_youtube_url(video_url) else "bestvideo[height<=480]+bestaudio/best",
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "max_filesize": 600 * 1024 * 1024,
        "quiet": True,
        "no_warnings": True
    }


    ydl_opts = ydl_opts_audio if audio_only else ydl_opts_video

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

        title = info.get("title", "download")

        downloaded_files = [
            os.path.join(output_path, file)
            for file in os.listdir(output_path)
        ]

        newest_file = max(downloaded_files, key=os.path.getmtime)

        return newest_file, title

def is_youtube_url(url):
    """Check if a URL is a valid YouTube URL"""
    youtube_patterns = [
        r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+",
        r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/watch\?v=[\w-]+",
        r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/shorts/[\w-]+",
        r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/embed/[\w-]+",
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

async def resolve_spotify(url):
    """Return a yt-dlp search query from a Spotify track URL"""
    sp = spotipy.Spotify()
    track = sp.track(url)
    artist = track["artists"][0]["name"]
    title = track["name"]
    return f"ytsearch1:{artist} - {title}", f"{artist} - {title}"

async def download_and_upload(interaction, session, download_url, title, status_msg):
    """Download file and upload to Catbox"""
    try:
        await status_msg.edit(
            content=f"⬇️ Downloading file..."
        )
        
        async with session.get(download_url, timeout=180) as file_response:
            if file_response.status != 200:
                await status_msg.edit(content=f"❌ Download failed: HTTP {file_response.status}")
                return
            
            file_data = await file_response.read()
            file_size_mb = len(file_data) / (1024 * 1024)
            
            if file_size_mb > 200:
                await status_msg.edit(content=f"❌ File too large: {file_size_mb:.1f}MB (max 600MB)")
                return
            
            await status_msg.edit(content=f"📤 Sending file to Discord ({file_size_mb:.1f}MB)...")

            # Send the audio file directly as a Discord attachment
            discord_file = discord.File(fp=io.BytesIO(file_data), filename=f"{title[:50]}.mp3")
            await interaction.followup.send(file=discord_file, content="✅ Download Complete!")
            # Update the status message to indicate completion
            await status_msg.edit(content="✅ File sent.")
    
    except asyncio.TimeoutError:
        await status_msg.edit(content="❌ Download timed out. File may be too large or server is slow.")
    except Exception as e:
        await status_msg.edit(content=f"❌ Error during download/upload: {str(e)}")

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})',
        r'watch\?v=([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

class SayCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="say", description="make amber say something")


    @app_commands.command(name="embed", description="say what you want in embed")
    @app_commands.describe(
        timestamp="add a timestamp",
        show_author="add your name",
        image="image url",
        color="embed color"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    @app_commands.allowed_installs(guilds=True, users=True)
    async def say_embed(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        footer: str,
        timestamp: bool = True,
        show_author: bool = False,
        image: Optional[discord.Attachment] = None,
        color: Literal["blue", "red", "green", "yellow", "purple", "random"] = "blue"
    ):
        # color map
        COLORS = {
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "yellow": discord.Color.yellow(),
            "purple": discord.Color.purple(),
            "random": discord.Color.random(),
        }

        embed = discord.Embed(
            title=name,
            description=description,
            color=COLORS[color]
        )

        if timestamp:
            embed.timestamp = datetime.now()

        embed.set_footer(text=footer)

        if show_author:
            embed.set_author(
                name=interaction.user.name,
                icon_url=interaction.user.display_avatar.url
            )

        if image:
            embed.set_image(url=image.url)

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="text", description="say what you want in embed")
    @app_commands.describe(
        message=      "message to send",
        show_author=  "add your name",
        image=        "image url",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    @app_commands.allowed_installs(guilds=True, users=True)
    async def say_text(
        self,
        interaction: discord.Interaction,
        message: str,
        show_author: bool = False,
        image: Optional[discord.Attachment] = None,
    ):

        content = message
        if show_author:
            content += f"-# - {interaction.user.display_name}"

        if image:
            await interaction.response.send_message(content, file=await image.to_file())
        else:
            await interaction.response.send_message(content)


async def utils_setup(bot):
    # ── say commands ────────────────────────────────────────────────
    bot.tree.add_command(SayCommands())

    # ── download command ────────────────────────────────────────────────
    @bot.tree.command(name="download", description="Download audio or video from a YouTube or Spotify URL.")
    @discord.app_commands.describe(url="YouTube or Spotify URL", format="audio or video")
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    async def download(
        interaction: discord.Interaction,
        url: str,
        format: Literal["audio", "video"] = "audio"
    ):
        await interaction.response.defer()
        status_msg = await interaction.followup.send("🔄 Processing your request...")

        try:
            search_query = url
            display_name = None

            if "spotify.com" in url:
                try:
                    await status_msg.edit(content="🔍 Resolving Spotify track...")
                    search_query, display_name = await resolve_spotify(url)
                    await status_msg.edit(content=f"🎵 Found: **{display_name}** — searching YouTube...")
                except Exception:
                    await status_msg.edit(content="❌ Couldn't find that Spotify track. Make sure it's a valid track URL (not a playlist or album).")
                    return

            await status_msg.edit(content=f"⬇️ Downloading {format}...")


            tmpdir = tempfile.mkdtemp()

            try:
                file_path, title = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: download_with_ytdlp(search_query, tmpdir, audio_only=(format == "audio"))
                )
            except TimeoutError:
                await status_msg.edit(content="❌ Download timed out — the file might be too large or the server is slow.")
                return
            except yt_dlp.utils.DownloadError as e:
                msg = str(e)
                if "Private video" in msg:
                    await status_msg.edit(content="❌ That video is private.")
                elif "This video is not available" in msg or "Video unavailable" in msg:
                    await status_msg.edit(content="❌ That video isn't available (it may be region-locked or deleted).")
                elif "age" in msg.lower():
                    await status_msg.edit(content="❌ That video is age-restricted and can't be downloaded.")
                elif "max filesize" in msg.lower() or "File is larger" in msg:
                    await status_msg.edit(content="❌ That file exceeds the 200MB limit.")
                else:
                    await status_msg.edit(content="❌ Couldn't download that video. It may be unavailable or unsupported.")
                return
            except Exception:
                await status_msg.edit(content="❌ Something went wrong during download. Try a different URL.")
                return

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            filename = os.path.basename(file_path)
            label = display_name or title

            if file_size_mb <= 25:
                await status_msg.edit(content=f"📤 Uploading to Discord ({file_size_mb:.1f}MB)...")
                discord_file = discord.File(fp=file_path, filename=filename)
                await interaction.followup.send(content=f"✅ **{label}** ({format})", file=discord_file)
                await status_msg.edit(content="✅ Done.")
            else:
                await status_msg.edit(content=f"📦 File is {file_size_mb:.1f}MB — too large for Discord, uploading to Catbox...")
                try:
                    uploader = CatboxUploader()
                    

                    catbox_url = await asyncio.get_event_loop().run_in_executor(
                        None,
                        uploader.upload_file,
                        file_path,
                        600
                    )
                    
                    if catbox_url and catbox_url.startswith("https://"):
                        await interaction.followup.send(content=f"✅ **{label}** ({format})\n{catbox_url}")
                        await status_msg.edit(content="✅ Done.")
                    else:
                        await status_msg.edit(content=f"❌ Couldn't upload to Litterbox. Response: {catbox_url}")
                except asyncio.TimeoutError:
                    await status_msg.edit(content="❌ Catbox upload timed out. The file might be too large.")
                except Exception as e:
                    await status_msg.edit(content="❌ Couldn't upload to Catbox. Try again later.")

        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception as e:
                print(f"Failed to clear temp directory: {e}")


async def handle_pin(message):
    content = (message.content or "").lower().strip()
    if content.startswith("!"):
        content = content[1:]

    if content not in ("pin", "unpin"):
        return False

    if not message.reference:
        return True

    replied = await message.channel.fetch_message(message.reference.message_id)

    if content == "pin":
        await replied.pin(reason=f"Pinned by {message.author}")
    else:
        await replied.unpin(reason=f"Unpinned by {message.author}")
        await message.add_reaction("❌")
    return True
