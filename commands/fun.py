from PIL import Image, ImageDraw, ImageFont, ImageFilter
from discord import app_commands, embeds
from discord.ext import commands
from os.path import pathsep
from typing import Optional
from pathlib import Path
from io import BytesIO
import statistics
import discord
import aiohttp
import random
import emoji
import json
import os
import io
import re

class ImageGenerator:
    """Handles image generation and manipulation."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.font_dir = root_dir / "assets" / "fonts"
    
    def get_fitting_font(self, font_path: str, text: str, max_width: int, starting_size: int = 180) -> ImageFont.FreeTypeFont:
        """Find the largest font size that fits the text within max_width."""
        font_size = starting_size
        
        while font_size > 1:
            font = ImageFont.truetype(font_path, font_size)
            if font.getlength(text) <= max_width:
                return font
            font_size -= 1
        
        return ImageFont.truetype(font_path, 1)
    
    def fit_text_into_box(self, draw: ImageDraw.Draw, text: str, font_path: str, 
                          max_width: int, max_height: int, start_size: int = 50) -> tuple:
        """Fit text into a box with word wrapping and size adjustment."""
        font_size = start_size
        pad = 20
        adjusted_width = max_width - 2 * pad
        adjusted_height = max_height - 2 * pad
        
        while font_size > 8:
            font = ImageFont.truetype(font_path, font_size)
            lines = self._wrap_text(draw, text, font, adjusted_width)
            
            total_height = sum(font.getbbox(line)[3] for line in lines)
            if total_height <= adjusted_height:
                return font, "\n".join(lines), pad
            
            font_size -= 1
        
        return ImageFont.truetype(font_path, 8), text, pad
    
    def _wrap_text(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, 
                   max_width: int) -> list[str]:
        """Wrap text to fit within max_width."""
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            
            # Handle long words that exceed max_width
            if draw.textlength(word, font=font) > max_width:
                for char in word:
                    test_char = current_line + char
                    if draw.textlength(test_char, font=font) <= max_width:
                        current_line = test_char
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = char
            elif draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    async def create_wanted_poster(self, user: discord.User, amount: int) -> BytesIO:
        """Create a wanted poster image with optimized memory usage."""
        template_path = self.root_dir / "assets" / "fun" / "wanted.png"
        font_path = self.font_dir / "wanted_font.ttf"
        
        # Fetch user avatar
        async with aiohttp.ClientSession() as session:
            async with session.get(user.display_avatar.url) as resp:
                avatar_bytes = await resp.read()
        
        # Load template first to get dimensions
        template = Image.open(str(template_path)).convert("RGBA")
        frame_width, frame_height = template.size
        
        # Process avatar directly onto template instead of keeping separate copy
        avatar = Image.open(BytesIO(avatar_bytes))
        avatar = avatar.convert("RGBA").resize((900, 900), Image.Resampling.LANCZOS)
        
        # Clear avatar_bytes from memory
        del avatar_bytes
        
        # Paste avatar directly onto template (reuse template as output)
        avatar_pos = ((frame_width - 900) // 2, 600)
        template.paste(avatar, avatar_pos, avatar)
        
        # Clear avatar from memory immediately after use
        del avatar
        
        # Add text
        draw = ImageDraw.Draw(template)
        
        try:
            name_font = self.get_fitting_font(str(font_path), user.display_name, 1000, 180)
            amount_font = ImageFont.truetype(str(font_path), 130)
        except OSError:
            name_font = ImageFont.load_default()
            amount_font = ImageFont.load_default()
        
        # Draw name
        name_bbox = draw.textbbox((0, 0), user.display_name, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_pos = ((frame_width - name_width) // 2, 1790)
        draw.text(name_pos, user.display_name, font=name_font, fill=(101, 67, 33))
        
        # Draw amount
        amount_text = f"{amount:,}"
        amount_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
        amount_width = amount_bbox[2] - amount_bbox[0]
        amount_pos = ((frame_width - amount_width) // 2, 2050)
        draw.text(amount_pos, amount_text, font=amount_font, fill=(139, 69, 19))
        
        # Save to bytes with optimized settings
        output_bytes = BytesIO()
        template.save(output_bytes, format='PNG', optimize=True)
        output_bytes.seek(0)
        
        # Clean up
        del template, draw
        
        return output_bytes
    
    async def create_quote_image(self, user: discord.User, message: str) -> BytesIO:
        """Create a quote/misquote image."""
        font_path = self.font_dir / "quote.ttf"
        
        # Fetch user avatar
        async with aiohttp.ClientSession() as session:
            async with session.get(user.display_avatar.url) as resp:
                avatar_bytes = await resp.read()
        
        # Create canvas
        canvas = Image.new("RGBA", (500, 250), "black")
        draw = ImageDraw.Draw(canvas)
        
        # Add avatar
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((250, 250))
        canvas.paste(avatar, (0, 0), avatar)
        
        # Add quote
        quote_font, wrapped_quote, pad = self.fit_text_into_box(
            draw, message, str(font_path), 230, 190, 25
        )
        
        # Calculate quote height for vertical centering
        quote_bbox = draw.multiline_textbbox((0, 0), wrapped_quote, font=quote_font)
        quote_height = quote_bbox[3] - quote_bbox[1]
        
        available_height = 170
        quote_y = 30 + (available_height - quote_height) // 2
        
        draw.multiline_text((270 + pad, quote_y), wrapped_quote, font=quote_font, fill=(200, 200, 200))
        
        draw.line((270, 200, 480, 200), fill=(200, 200, 200), width=2)
        
        name_font, wrapped_name, pad = self.fit_text_into_box(
            draw, f"- @{user.display_name}", str(font_path), 250, 60, 15
        )
        draw.multiline_text((270 + pad, 210), wrapped_name, font=name_font, fill=(255, 240, 200))
        
        # Save to bytes
        output_bytes = BytesIO()
        canvas.save(output_bytes, format="PNG")
        output_bytes.seek(0)
        return output_bytes

    def generate_inkblot(self, width: int = 500, height: int = 700) -> Image.Image:
        """Generate a random Rorschach-style inkblot."""
        half_width = width // 2
        
        # Color palettes
        colors = ['white', 'honeydew', 'black', '#432323', '#0C2B4E', "#7A2828"]
        dark_colors = ['black', '#432323', '#0C2B4E', '#7A2828', 'darkblue', 'darkred']
        light_colors = ['white', 'honeydew', 'lightblue', 'lightyellow']
        
        # Choose background and fill colors
        bg_color = random.choice(colors)
        fill_color = (random.choice(light_colors) if bg_color in dark_colors 
                     else random.choice(dark_colors))
        
        # Create image
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw blobs
        num_blobs = random.randint(10, 25)
        for _ in range(num_blobs):
            self._draw_random_blob(draw, half_width, height, bg_color, fill_color)
        
        # Add noise
        self._add_noise(draw, half_width, height, colors)
        
        # Add central feature
        self._draw_central_feature(draw, half_width, height, fill_color)
        
        # Apply blur and mirror
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        left_half = img.crop((0, 0, half_width, height))
        right_half = left_half.transpose(Image.FLIP_LEFT_RIGHT)
        img.paste(right_half, (half_width, 0))
        
        return img
    
    def _draw_random_blob(self, draw: ImageDraw.Draw, half_width: int, height: int, 
                          bg_color: str, fill_color: str):
        """Draw a random blob shape."""
        x = random.randint(0, half_width - 50)
        y = random.randint(50, height - 50)
        w_size = random.randint(30, 170)
        h_size = random.randint(30, 170)
        
        shape_type = random.choice(['irregular', 'blob', 'irregular'])
        
        if shape_type == 'blob':
            draw.ellipse([x, y, x + w_size, y + h_size], fill=bg_color)
        else:
            num_circles = random.randint(5, 10) if shape_type == 'irregular' else random.randint(3, 7)
            offset_range = 40 if shape_type == 'irregular' else 30
            size_range = (30, 90) if shape_type == 'irregular' else (20, 77)
            
            for _ in range(num_circles):
                offset_x = random.randint(-offset_range, offset_range)
                offset_y = random.randint(-offset_range, offset_range)
                circle_size = random.randint(*size_range)
                draw.ellipse([
                    x + offset_x, y + offset_y,
                    x + offset_x + circle_size, y + offset_y + circle_size
                ], fill=fill_color)
    
    def _add_noise(self, draw: ImageDraw.Draw, half_width: int, height: int, colors: list):
        """Add random noise to the image."""
        for _ in range(random.randint(100, 300)):
            x = random.randint(0, half_width)
            y = random.randint(0, height)
            size = random.randint(1, 3)
            draw.ellipse([x, y, x + size, y + size], fill=random.choice(colors))
    
    def _draw_central_feature(self, draw: ImageDraw.Draw, half_width: int, 
                             height: int, fill_color: str):
        """Draw a central feature with multiple layers."""
        center_x = random.randint(50, half_width - 50)
        center_y = random.randint(100, height - 100)
        num_layers = random.randint(5, 15)
        
        for _ in range(num_layers):
            offset_x = random.randint(-40, 40)
            offset_y = random.randint(-40, 40)
            size = random.randint(30, 120)
            
            draw.ellipse([
                center_x + offset_x - size // 2,
                center_y + offset_y - size // 2,
                center_x + offset_x + size // 2,
                center_y + offset_y + size // 2
            ], fill=fill_color)


class OFCType(discord.Enum):
    SFW = "sfw"
    NSFW = "nsfw"



async def fun_setup(bot: commands.Bot):
    """Set up fun commands for the bot."""
    ROOT_DIR = Path(__file__).resolve().parent.parent
    OFC_SFW = ROOT_DIR / "assets" / "ofc" / "sfw"
    OFC_NSFW = ROOT_DIR / "assets" / "ofc" / "nsfw"
    img_gen = ImageGenerator(ROOT_DIR)
    api_key = os.getenv('GIPHY_API')
    
    # ==================== Wanted Poster ====================
    @bot.tree.command(name="wanted", description="Create a wanted poster!")
    @app_commands.describe(
        user="The criminal you want the poster for.",
        amount="The bounty amount."
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wanted(interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(thinking=True)
        try:
            output_bytes = await img_gen.create_wanted_poster(user, amount)
            file = discord.File(output_bytes, filename=f"wanted_{user.name}.png")
            await interaction.followup.send(file=file)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    # ==================== Misquote ====================
    @bot.tree.command(name="misquote", description="Create a fake quote image")
    @app_commands.describe(
        message="What did they say?",
        user="Who said it?"
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def misquote(interaction: discord.Interaction, user: discord.User, message: str):
        await interaction.response.defer()
        try:
            output_bytes = await img_gen.create_quote_image(user, message)
            file = discord.File(output_bytes, filename=f"quote_{user.name}.png")
            await interaction.followup.send(file=file)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    # ==================== Rorschach Test ====================
    @bot.tree.command(name="rarch", description="Generate an inkblot image")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rarch(interaction: discord.Interaction):
        inkblot_image = img_gen.generate_inkblot()
        
        with io.BytesIO() as image_binary:
            inkblot_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename='inkblot.png')
            
            embed = discord.Embed(title="What do you see?")
            embed.set_image(url="attachment://inkblot.png")
            await interaction.response.send_message(embed=embed, file=file)
    
    # ==================== Animal Commands ====================
    @bot.tree.command(name="duck", description="Get a random duck image")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def duck(interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://random-d.uk/api/v2/list") as resp:
                    data = await resp.json()
                    gifs = data.get("gifs", [])
                    gif_url = (f"https://random-d.uk/api/{random.choice(gifs)}" 
                              if gifs else "https://random-d.uk/api/random")
            
            embed = discord.Embed(title="Random Duck!")
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Error",
                    description=f"```log\nError:\n{str(e)}\n```",
                    color=discord.Color.red()
                )
            )
    
    @bot.tree.command(name="rotta", description="Get a random rat gif")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rat(interaction: discord.Interaction):
        await interaction.response.defer()
        
        rat_url = f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=rat&rating=G"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(rat_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gif_url = data['data']['images']['original']['url']
                        
                        embed = discord.Embed(title="Random Rat!", color=discord.Color.dark_green())
                        embed.set_image(url=gif_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            embed=discord.Embed(
                                title="Error",
                                description=f"Could not fetch a rat gif. (Status: {resp.status})",
                                color=discord.Color.red()
                            )
                        )
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Error",
                    description=f"```log\nError:\n{str(e)}\n```",
                    color=discord.Color.red()
                )
            )
    
    @bot.tree.command(name="cat", description="Get a random cat gif")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def cat(interaction: discord.Interaction):
        cat_url = "https://api.thecatapi.com/v1/images/search?mime_types=gif"
        colors = [discord.Color.orange(), 0xFFFFFF, discord.Color.pink(), 
                 discord.Color.from_rgb(0, 0, 0)]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(cat_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gif_url = data[0]['url']
                        
                        embed = discord.Embed(title="Random Cat!", color=random.choice(colors))
                        embed.set_image(url=gif_url)
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message(
                            embed=discord.Embed(
                                title="Error",
                                description=f"Could not fetch a cat gif. (Status: {resp.status})",
                                color=discord.Color.red()
                            )
                        )
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Error",
                    description=f"```log\nError:\n{str(e)}\n```",
                    color=discord.Color.red()
                )
            )
    
    # ==================== Out of Context ====================
    @bot.tree.command(name="ofc", description="Get a random out of context image")
    @app_commands.describe(type="Choose whether the image is SFW or NSFW")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ofc(interaction: discord.Interaction, type: OFCType = OFCType.SFW):
        # Check NSFW restrictions
        if type == OFCType.NSFW:
            if interaction.guild is not None:
                channel = interaction.channel
                if not isinstance(channel, discord.TextChannel) or not channel.is_nsfw():
                    return await interaction.response.send_message(
                        "NSFW images can only be requested in NSFW channels.",
                        ephemeral=True
                    )
        
        img_dir = OFC_SFW if type == OFCType.SFW else OFC_NSFW
        img = random.choice(os.listdir(img_dir))
        
        embed = discord.Embed(color=discord.Color.purple())
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="Thanks to AMTA community <3")
        
        await interaction.response.send_message(
            file=discord.File(img_dir / img),
            embed=embed
        )
    
    # ==================== Games ====================
    @bot.tree.command(name="8ball", description="Ask the magic 8 ball a question")
    @app_commands.describe(question="Your question for the magic 8 ball")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def eight_ball(interaction: discord.Interaction, question: str):
        answers = [
            "It is certain", "It is decidedly so", "Without a doubt",
            "Yes, definitely", "You may rely on it", "As I see it, yes",
            "Most likely", "Outlook good", "Yes", "Signs point to yes",
            "Reply hazy, try again", "Ask again later", "Better not tell you now",
            "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful"
        ]
        
        embed = discord.Embed(title="🎱 The Magic 8 Ball 🎱", color=discord.Color.blurple())
        embed.add_field(name="Question:", value=question, inline=False)
        embed.add_field(name="Answer:", value=random.choice(answers), inline=False)
        embed.set_footer(text="Amber is not responsible for any decisions based on this answer.")
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="coinflip", description="Flip a coin")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def coinflip(interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(title="Coin Flip!", color=discord.Color.gold())
        embed.description = f"The coin landed on **{result}**!"
        
        await interaction.response.send_message(embed=embed)
    @bot.tree.command(name="no", description="say no!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def no(interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://naas.isalman.dev/no") as resp:
                data= await resp.json()
    

        embed = discord.Embed(
            color=discord.Color.red(),
            title="no!",
            description=f"{data.get('reason', 'no response')}"
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="yes", description="agreement reason")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def yes(interaction: discord.Interaction):
        with open("assets/fun/yes.json") as yes:
            reasons = json.load(yes)
        response = random.choice(reasons)
        embed = discord.Embed(
            color=discord.Color.brand_green(),
            title="yes!",
            description=response
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="rate", description="give you detailed rating")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rate(interaction: discord.Interaction, user: Optional[discord.User] = None):
        try:
            await interaction.response.defer()
            user = user or interaction.user
            
            ratings = {
                "Smort": random.randint(0, 100),
                "Funny": random.randint(0, 100),
                "Rizz": random.randint(0, 100),
                "Hot": random.randint(0, 100),
                "cute": random.randint(0, 100),
                "gay": random.randint(0, 100)
            }

            mean_rating = statistics.mean(ratings.values())

            with open("assets/fun/rating.json", "r") as f:
                data = json.load(f)

            if mean_rating >= 75:
                description = data.get("high", [])
            elif mean_rating >= 40:
                description = data.get("medium", [])
            else:
                description = data.get("low", [])

            embed = discord.Embed(
                title=f"Rating for {user.display_name}",
                color=discord.Color.pink(),
                description=random.choice(description).format(**ratings)
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Smort", value=f"**{ratings['Smort']}%** 🤓", inline=True)
            embed.add_field(name="Funny", value=f"**{ratings['Funny']}%** 😜", inline=True)
            embed.add_field(name="Rizz", value=f"**{ratings['Rizz']}%** 😗", inline=True)
            embed.add_field(name="Hot", value=f"**{ratings['Hot']}%** 🔥", inline=True)
            embed.add_field(name="Cute", value=f"**{ratings['cute']}%** 🫶", inline=True)
            embed.add_field(name="gay", value=f"**{ratings['gay']}%** 🏳️‍🌈", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Error",
                        description=f"```log\nError:\n{str(e)}\n```",
                        color=discord.Color.red()
                    )
                )
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Error",
                        description=f"```log\nError:\n{str(e)}\n```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

async def handle_4k(bot: commands.Bot, message: discord.Message):
    """Handle the '4k' message reply command."""
    if message.author.bot or message.content.lower().strip() != "4k":
        return
    
    if not message.reference or not getattr(message.reference, "message_id", None):
        await message.reply("You must **reply** to a message to use `4k`.", delete_after=2)
        return
    
    try:
        replied = await message.channel.fetch_message(message.reference.message_id)
    except Exception:
        await message.reply("Can't read the replied message.", delete_after=2)
        return
    
    ROOT_DIR = Path(__file__).resolve().parent.parent
    img_gen = ImageGenerator(ROOT_DIR)
    
    try:
        output_bytes = await img_gen.create_quote_image(replied.author, replied.content or "")
        await message.reply(file=discord.File(output_bytes, filename=f"quote_{replied.author.name}.png"))
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}", delete_after=5)
    
    await bot.process_commands(message)
