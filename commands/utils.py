import discord
import aiohttp
import spotipy
import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

async def utils_setup(bot):
    @bot.tree.command(name="download", description="Download audio from a URL.")
    @discord.app_commands.describe(url="The URL of the audio to download.")
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    async def download(interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        
        try:
            video_url = url
            title = "audio"

            if "spotify.com" in url:
                sp = spotipy.Spotify()
                try:
                    track_info = sp.track(url)
                    artist = track_info['artists'][0]['name']
                    title = track_info['name']
                    await interaction.followup.send(
                        f"🔍 Spotify track: **{artist} - {title}**\n"
                        f"Please search this on YouTube and use `/download` with the YouTube URL."
                    )
                    return
                except Exception as e:
                    await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
                    return
            
            status_msg = await interaction.followup.send("🔄 Processing your request...")
            
            async with aiohttp.ClientSession() as session:
                
                video_id = extract_youtube_id(video_url)
                
                if not video_id:
                    await status_msg.edit(content="❌ Please provide a valid YouTube URL")
                    return
                
                try:
                    rapidapi_key = os.getenv('RAPIDAPI_KEY')
                    
                    if rapidapi_key:
                        await status_msg.edit(content="🎵 Fetching download link...")
                        
                        api_url = f"https://youtube-mp36.p.rapidapi.com/dl"
                        
                        params = {"id": video_id}
                        
                        headers = {
                            "X-RapidAPI-Key": rapidapi_key,
                            "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com"
                        }
                        
                        async with session.get(api_url, params=params, headers=headers, timeout=30) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if data.get("status") == "ok":
                                    download_url = data.get("link")
                                    title = data.get("title", "audio")
                                    
                                    if download_url:
                                        await download_and_upload(interaction, session, download_url, title, status_msg)
                                        return
                    else:
                        print("RAPIDAPI_KEY not found in .env, skipping Method 1")
                
                except Exception as e:
                    print(f"RapidAPI method failed: {e}")
                
                try:
                    await status_msg.edit(content="🔄 Trying alternative method...")
                    
                    search_url = "https://yt1s.com/api/ajaxSearch/index"
                    
                    search_payload = {
                        "q": f"https://www.youtube.com/watch?v={video_id}",
                        "vt": "mp3"
                    }
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "https://yt1s.com",
                        "Referer": "https://yt1s.com/"
                    }
                    
                    async with session.post(search_url, data=search_payload, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("status") == "ok":
                                title = data.get("title", "audio")
                                vid = data.get("vid")
                                
                                mp3_links = data.get("links", {}).get("mp3", {})
                                if mp3_links:
                                    best_quality = max(mp3_links.keys())
                                    k_value = mp3_links[best_quality].get("k")
                                    
                                    await status_msg.edit(content="🎵 Converting to MP3...")
                                    
                                    convert_url = "https://yt1s.com/api/ajaxConvert/convert"
                                    convert_payload = {
                                        "vid": vid,
                                        "k": k_value
                                    }
                                    
                                    async with session.post(convert_url, data=convert_payload, headers=headers, timeout=60) as conv_response:
                                        if conv_response.status == 200:
                                            conv_data = await conv_response.json()
                                            
                                            if conv_data.get("status") == "ok":
                                                download_url = conv_data.get("dlink")
                                                
                                                if download_url:
                                                    await download_and_upload(interaction, session, download_url, title, status_msg)
                                                    return
                
                except Exception as e:
                    print(f"YT1S method failed: {e}")
                
                try:
                    await status_msg.edit(content="🔄 Trying third method...")
                    
                    savefrom_url = f"https://api.savefrom.net/info"
                    
                    params = {
                        "url": f"https://www.youtube.com/watch?v={video_id}"
                    }
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0"
                    }
                    
                    async with session.get(savefrom_url, params=params, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            text = await response.text()
                            import json
                            data = json.loads(text.strip('[]'))
                            
                            if data and isinstance(data, dict):
                                urls = data.get("url", [])
                                title = data.get("meta", {}).get("title", "audio")
                                
                                for url_data in urls:
                                    if url_data.get("type") == "audio" or "audio" in url_data.get("ext", ""):
                                        download_url = url_data.get("url")
                                        if download_url:
                                            await download_and_upload(interaction, session, download_url, title, status_msg)
                                            return
                
                except Exception as e:
                    print(f"SaveFrom method failed: {e}")
                
                await status_msg.edit(
                    content="❌ All download methods failed.\n\n"
                    "**If you haven't set up RapidAPI yet:**\n"
                    "1. Get a free key from https://rapidapi.com/ytjar/api/youtube-mp36\n"
                    "2. Add `RAPIDAPI_KEY=your_key_here` to your .env file\n"
                    "3. Free tier: 500 requests/month\n\n"
                    "Alternatively, try a different/shorter YouTube video."
                )
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def download_and_upload(interaction, session, download_url, title, status_msg):
    """Download file and upload to Catbox"""
    try:
        await status_msg.edit(content="⬇️ Downloading audio file...")
        
        async with session.get(download_url, timeout=180) as file_response:
            if file_response.status != 200:
                await status_msg.edit(content=f"❌ Download failed: HTTP {file_response.status}")
                return
            
            file_data = await file_response.read()
            file_size_mb = len(file_data) / (1024 * 1024)
            
            if file_size_mb > 200:
                await status_msg.edit(content=f"❌ File too large: {file_size_mb:.1f}MB (max 200MB)")
                return
            
            await status_msg.edit(content=f"☁️ Uploading to Catbox ({file_size_mb:.1f}MB)...")
            
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
            
            form = aiohttp.FormData()
            form.add_field('reqtype', 'fileupload')
            form.add_field('fileToUpload', file_data, filename=f"{safe_title}.mp3", content_type='audio/mpeg')
            
            async with session.post('https://catbox.moe/user/api.php', data=form, timeout=180) as upload_response:
                if upload_response.status != 200:
                    await status_msg.edit(content=f"❌ Upload failed: HTTP {upload_response.status}")
                    return
                
                catbox_url = (await upload_response.text()).strip()
                
                if catbox_url.startswith('http'):
                    embed = discord.Embed(
                        title="✅ Download Complete!",
                        description=f"**{title[:100]}**\n\n[📥 Click to Download]({catbox_url})\n\n📊 Size: {file_size_mb:.1f}MB",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Permanent link • Hosted on Catbox.moe")
                    await status_msg.edit(content=None, embed=embed)
                else:
                    await status_msg.edit(content=f"❌ Catbox upload error: {catbox_url}")
    
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



async def handle_pin(bot, message):
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
