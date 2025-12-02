from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import discord
import aiohttp
from discord import app_commands
from pathlib import Path

async def fun_setup(bot):
    @bot.tree.command(name="wanted", description="ye criminal mate!")
    @app_commands.describe(user="The criminal you want the poster for.")
    @app_commands.describe(amount="The amount for the bounty.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wanted(interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(thinking=True)
        try:
            ROOT_DIR = Path(__file__).resolve().parent.parent
            template_path = ROOT_DIR / "assets" / "fun" / "wanted.png"
            font_path = ROOT_DIR / "assets" / "fonts" / "wanted_font.ttf"
            
            template_path = str(template_path)
            font_path = str(font_path)
            
            user_avatar_url = user.display_avatar.url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(user_avatar_url) as resp:
                    avatar_bytes = await resp.read()
            
            image_avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
            image_frame = Image.open(template_path).convert("RGBA")
            image_avatar = image_avatar.resize((900, 900))
            image_frame_width, image_frame_height = image_frame.size
            output = image_frame.copy()
            image_avatar_width, image_avatar_height = image_avatar.size
            image_avatar_pos = ((image_frame_width - image_avatar_width) // 2, 600)
            output.paste(image_avatar, image_avatar_pos, image_avatar)
            try:
                def get_fitting_font(font_path, text, max_width, starting_size=180):
                    font_size = starting_size

                    while font_size > 1:
                        font = ImageFont.truetype(font_path, font_size)
                        text_width = font.getlength(text)

                        if text_width <= max_width:
                            return font
                        
                        font_size -= 1

                    return ImageFont.truetype(font_path, 1)

                max_font_size_name = 180
                name_max_width = 1000

                name_font = get_fitting_font(font_path, user.display_name, name_max_width, starting_size=max_font_size_name)
                amount_font = ImageFont.truetype(font_path, 130)
            except OSError as font_error:
                name_font = ImageFont.load_default()
                amount_font = ImageFont.load_default()
            
            draw = ImageDraw.Draw(output)
            name_text = user.display_name
            
            name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            
            name_position = ((image_frame_width - name_width) // 2, 1790)
            draw.text(name_position, name_text, font=name_font, fill=(101, 67, 33))
            
            amount_text = f"{amount:,}"
            amount_bbox = draw.textbbox((0, 0), amount_text, font=amount_font)
            amount_width = amount_bbox[2] - amount_bbox[0]
            
            amount_position = ((image_frame_width - amount_width) // 2, 2050)
            draw.text(amount_position, amount_text, font=amount_font, fill=(139, 69, 19))
            
            output_bytes = BytesIO()
            output.save(output_bytes, format='PNG')
            output_bytes.seek(0)
            
            file = discord.File(output_bytes, filename=f"wanted_{user.name}.png")
            await interaction.followup.send(file=file)
            
        except Exception as e:
            await interaction.followup.send(f"An error occurred while processing the image.\n{str(e)}")
