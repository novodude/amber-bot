from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import discord
import aiohttp
from discord import app_commands, message
from discord.ext import commands
from pathlib import Path
import os

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


    @bot.tree.command(name="misquote", description="spreading misinformation is fun :P!")
    @app_commands.describe(message="what did they say?")
    @app_commands.describe(user="who said what?")
    async def misinformation(interaction: discord.Interaction, user: discord.User, message: str):
        await interaction.response.defer()

        ROOT_DIR = Path(__file__).resolve().parent.parent
        font_path = str(ROOT_DIR / "assets" / "fonts" / "quote.ttf")
        user_avatar_url = user.display_avatar.url
        
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_url) as resp:
                avatar_bytes = await resp.read()

        canvas = Image.new("RGBA", (500, 250), "black")
        draw = ImageDraw.Draw(canvas)

        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((250, 250))
        canvas.paste(avatar, (0, 0), avatar)

        def fit_text_into_box(text, max_width, max_height, start_size=50):
            font_size = start_size
            pad = 20
            adjusted_width = max_width - 2*pad
            adjusted_height = max_height - 2*pad

            while font_size > 8:
                font = ImageFont.truetype(font_path, font_size)
                lines = []
                words = text.split()
                line = ""

                for w in words:
                    test = line + (" " if line else "") + w
                    if draw.textlength(w, font=font) > adjusted_width:
                        chars = list(w)
                        for c in chars:
                            test2 = line + c
                            if draw.textlength(test2, font=font) <= adjusted_width:
                                line = test2
                            else:
                                lines.append(line)
                                line = c
                    elif draw.textlength(test, font=font) <= adjusted_width:
                        line = test
                    else:
                        lines.append(line)
                        line = w
                lines.append(line)

                total_h = sum(font.getbbox(l)[3] for l in lines)
                if total_h <= adjusted_height:
                    return font, "\n".join(lines), pad
                font_size -= 1

            return ImageFont.truetype(font_path, 8), text, pad

        name_font, wrapped_name, pad = fit_text_into_box(f"- @{user.display_name}", 250, 60, 15)
        draw.text((270 + pad, 210), wrapped_name, font=name_font, fill=(255, 240, 200))

        quote_font, wrapped_quote, pad = fit_text_into_box(message, 230, 180, 25)
        draw.text((270 + pad, 90), wrapped_quote, font=quote_font, fill=(200, 200, 200))

        draw.line((270, 200, 480, 200), fill=(200, 200, 200), width=2)
        draw.line((270, 200, 480, 200), fill=(200, 200, 200), width=2)
        output_bytes = BytesIO()
        canvas.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        await interaction.followup.send(
            file=discord.File(output_bytes, filename=f"quote_{user.name}.png")
        )

async def register_events(bot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        content = (message.content or "").lower().strip()

        if content != "4k":  
            return

        if not message.reference or not getattr(message.reference, "message_id", None):
            await message.reply("You must **reply** to a message to use `4k`.", delete_after=2)
            return

        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
        except:
            await message.reply("Can't read the replied message.", delete_after=2)
            return

        user = replied.author
        text = replied.content or ""

        ROOT_DIR = Path(__file__).resolve().parent.parent
        font_path = str(ROOT_DIR / "assets" / "fonts" / "quote.ttf")

        user_avatar_url = user.display_avatar.url
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_url) as resp:
                avatar_bytes = await resp.read()

        canvas = Image.new("RGBA", (500, 250), "black")
        draw = ImageDraw.Draw(canvas)

        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((250, 250))
        canvas.paste(avatar, (0, 0), avatar)

        def fit_text_into_box(text, max_width, max_height, start_size=50):
            font_size = start_size
            pad = 20  # space from edges
            adjusted_width = max_width - 2*pad
            adjusted_height = max_height - 2*pad

            while font_size > 8:
                font = ImageFont.truetype(font_path, font_size)
                lines = []
                words = text.split()
                line = ""

                for w in words:
                    test = line + (" " if line else "") + w
                    if draw.textlength(w, font=font) > adjusted_width:
                        chars = list(w)
                        for c in chars:
                            test2 = line + c
                            if draw.textlength(test2, font=font) <= adjusted_width:
                                line = test2
                            else:
                                lines.append(line)
                                line = c
                    elif draw.textlength(test, font=font) <= adjusted_width:
                        line = test
                    else:
                        lines.append(line)
                        line = w
                lines.append(line)

                total_h = sum(font.getbbox(l)[3] for l in lines)
                if total_h <= adjusted_height:
                    return font, "\n".join(lines), pad  # return pad to use when drawing
                font_size -= 1

            return ImageFont.truetype(font_path, 8), text, pad

        name_font, wrapped_name, pad = fit_text_into_box(f"- @{user.display_name}", 250, 60, 15)
        draw.text((270 + pad, 210), wrapped_name, font=name_font, fill=(255, 240, 200))

        quote_font, wrapped_quote, pad = fit_text_into_box(text, 230, 180, 25)
        draw.text((270 + pad, 90), wrapped_quote, font=quote_font, fill=(200, 200, 200))

        draw.line((270, 200, 480, 200), fill=(200, 200, 200), width=2)

        output_bytes = BytesIO()
        canvas.save(output_bytes, format="PNG")
        output_bytes.seek(0)

        await message.reply(
            file=discord.File(output_bytes, filename=f"quote_{user.name}.png")
        )

        await bot.process_commands(message)

