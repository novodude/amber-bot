from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import discord
import aiohttp
import random
from discord import app_commands, message
from discord.ext import commands
from pathlib import Path
import os
import io


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

    def generate_inkblot(width=500, height=700):
        half_width = width // 2
        random_color = ['white', 'honeydew','black', '#432323', '#0C2B4E', "#7A2828"]
        bg_color = random.choice(random_color)
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        dark = ['black', '#432323', '#0C2B4E', '#7A2828', 'darkblue', 'darkred']
        light = ['white', 'honeydew', 'lightblue', 'lightyellow']

        if bg_color in ['black', '#432323', '#0C2B4E', '#7A2828']:
            fill_color = random.choice(light) 
        else:
            fill_color = random.choice(dark)
        num_blobs = random.randint(10, 25)
        
        for _ in range(num_blobs):
            x = random.randint(0, half_width - 50)
            y = random.randint(50, height - 50)        
            width_size = random.randint(30, 170)
            height_size = random.randint(30, 170)        
            shape_type = random.choice([ 'irregular', 'blob', 'irregular'])

            if shape_type == 'blob':
                draw.ellipse([x, y, x + width_size, y + height_size], fill=bg_color)
            elif shape_type == 'irregular':
                num_circles = random.randint(5, 10)
                for _ in range(num_circles):
                    offset_x = random.randint(-40, 40)
                    offset_y = random.randint(-40, 40)
                    circle_size = random.randint(30, 90)
                    draw.ellipse(
                        [x + offset_x, y + offset_y, 
                        x + offset_x + circle_size, y + offset_y + circle_size],
                        fill=fill_color
                    )
            else:
                num_circles = random.randint(3, 7)
                for _ in range(num_circles):
                    offset_x = random.randint(-30, 30)
                    offset_y = random.randint(-30, 30)
                    circle_size = random.randint(20, 77)
                    draw.ellipse(
                        [x + offset_x, y + offset_y, 
                        x + offset_x + circle_size, y + offset_y + circle_size],
                        fill=fill_color
                    )
            

        for _ in range(random.randint(100, 300)):
            noise_x = random.randint(0, half_width)
            noise_y = random.randint(0, height)
            noise_size = random.randint(1, 3)
            draw.ellipse(
                [noise_x, noise_y, noise_x + noise_size, noise_y + noise_size],
                fill=random_color[random.randint(0, len(random_color)-1)]
            )


        for _ in range(num_blobs):
            center_x = random.randint(50, half_width - 50)
            center_y = random.randint(100, height - 100)
        
        num_layers = random.randint(5, 15)
        for layer in range(num_layers):
            offset_x = random.randint(-40, 40)
            offset_y = random.randint(-40, 40)
            size = random.randint(30, 120)
            
            draw.ellipse(
                [center_x + offset_x - size//2,
                 center_y + offset_y - size//2,
                 center_x + offset_x + size//2,
                 center_y + offset_y + size//2],
                fill=fill_color
            )

        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        left_half = img.crop((0, 0, half_width, height))
        right_half = left_half.transpose(Image.FLIP_LEFT_RIGHT)
        img.paste(right_half, (half_width, 0))

        return img
    @bot.tree.command(name="rarch", description="Generate a inkblot image.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rarch(interaction: discord.Interaction):
        inkblot_image = generate_inkblot()
        with io.BytesIO() as image_binary:
            inkblot_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename='inkblot.png')
            embed = discord.Embed(title="what do you see?")
            embed.set_image(url="attachment://inkblot.png")
            await interaction.response.send_message(embed=embed, file=file)



    api_key = os.getenv('GIPHY_API')
    @bot.tree.command(name="duck", description="random duck yay")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def duck(interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://random-d.uk/api/v2/list") as resp:
                    data = await resp.json()
                    gifs = data.get("gifs", [])
                    if gifs:
                        random_gif = random.choice(gifs)
                        gif_url = f"https://random-d.uk/api/{random_gif}"
                    else:
                        gif_url = "https://random-d.uk/api/random"
            embed = discord.Embed(title="Random Duck!")
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Error", 
                    description=f"```log\n\nError:\n{str(e)}\n\n```",
                    color=discord.Color.red()
                )
            )
    @bot.tree.command(name="rat", description="look at them ratting around")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rat(interaction: discord.Interaction):
        await interaction.response.defer()
        api = api_key
        rat_url = "https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=rat&rating=G"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(rat_url.format(api_key=api)) as resp:
                    if resp.status == 200:  # SUCCESS
                        data = await resp.json()
                        gif_url = data['data']['images']['original']['url']
                        
                        embed = discord.Embed(title="Random Rat!", color=discord.Color.dark_green())
                        embed.set_image(url=gif_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="Error", 
                            description=f"Could not fetch a rat gif at this time. (Status: {resp.status})", 
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Error", 
                    description=f"```log\n\nError:\n{str(e)}\n\n```",
                    color=discord.Color.red()
                )
            )

    @bot.tree.command(name="cat", description="orange, white, black omg they're pink too :3")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def cat(interaction: discord.Interaction):
        cat_url = "https://api.thecatapi.com/v1/images/search?mime_types=gif"
        
        clr = [discord.Color.orange(), 0xFFFFFF, discord.Color.pink(), discord.Color.from_rgb(0,0,0)]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(cat_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        gif_url = data[0]['url']
                        
                        embed = discord.Embed(title="Random Cat!", color=random.choice(clr))
                        embed.set_image(url=gif_url)
                        await interaction.response.send_message(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="Error", 
                            description=f"Could not fetch a cat gif at this time. (Status: {resp.status})", 
                            color=discord.Color.red()
                        )
                        await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Error", 
                    description=f"```log\n\nError:\n{str(e)}\n\n```",
                    color=discord.Color.red()
                )
            )

# Path to the repo root
    ROOT_DIR = Path(__file__).resolve().parent.parent
    OFC_SFW = ROOT_DIR / "assets" / "ofc" / "sfw"
    OFC_NSFW = ROOT_DIR / "assets" / "ofc" / "nsfw"

    async def ofc_setup(bot):

        class OFCType(discord.Enum):
            SFW = "sfw"
            NSFW = "nsfw"

        @bot.tree.command(name="ofc", description="out of context image :3")
        @app_commands.describe(type="Choose whether the image is SFW or NSFW")
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        @app_commands.allowed_installs(guilds=True, users=True)
        async def ofc(interaction: discord.Interaction, type: OFCType = OFCType.SFW):

            # check if NSFW is selected in a non-NSFW channel
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
            embed.set_footer(text="thanks to AMTA community <3")

            await interaction.response.send_message(
                file=discord.File(img_dir / img),
                embed=embed
            )

async def handle_4k(bot, message):
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

