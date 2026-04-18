from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from discord import app_commands
from pathlib import Path
from io import BytesIO
from typing import Literal
import aiohttp
import discord
import random
import math
import io

ROOT_DIR = Path(__file__).resolve().parent.parent

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
    
    
    def caption_image(self, image: Image.Image, caption: str) -> Image.Image:
        """Add a caption to the top of an image."""
        width, height = image.size
        caption_height = 50

        new_img = image.copy().convert("RGBA")
        draw = ImageDraw.Draw(new_img)

        font_path = self.font_dir / "caption.ttf"

        try:
            font = self.get_fitting_font(str(font_path), caption, width - 20, 60)
        except OSError:
            font = ImageFont.load_default()

        # Measure text
        text_bbox = draw.textbbox((0, 0), caption, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Center horizontally, small padding from top
        text_x = (width - text_width) // 2
        text_y = (height - caption_height + (caption_height - text_height) // 2) - 20

        draw.text(
            (text_x, text_y),
            caption,
            font=font,
            fill=(255, 255, 255),
            stroke_width=4,
            stroke_fill=(0, 0, 0)
        )

        return new_img

    def memeify_image(self, image: Image.Image, bottom: bool, caption: str) -> Image.Image:
        width, height = image.size
        padding = 200

        # Create canvas
        new_img = Image.new("RGBA", (width, height + padding), "black")

        if bottom:
            new_img.paste(image, (0, 0))          # caption at bottom
            text_area_y = height
        else:
            new_img.paste(image, (0, padding))    # caption at top
            text_area_y = 0

        draw = ImageDraw.Draw(new_img)
        font_path = self.font_dir / "caption.ttf"

        # Fit text to full width
        font, wrapped_text, _ = self.fit_text_into_box(
            draw,
            caption.upper(),
            str(font_path),
            width - 40,
            padding - 20,
            80
        )

        # Center text in the padding area
        text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = (width - text_width) // 2
        text_y = text_area_y + (padding - text_height) // 2

        draw.multiline_text(
            (text_x, text_y),
            wrapped_text,
            font=font,
            fill=(255, 255, 255),
            align="center",
            stroke_width=5,
            stroke_fill=(0, 0, 0)
        )

        return new_img

    def grayscale(self, image: Image.Image) -> Image.Image:
        return image.convert("L").convert("RGBA")
    
    def blur(self, image: Image.Image) -> Image.Image:
        return image.filter(ImageFilter.BoxBlur(radius=5))
    
    def rotate(self, image: Image.Image, angle: int) -> Image.Image:
        return image.rotate(angle)

    def flip(self, image: Image.Image, axis) -> Image.Image:
        if axis == "top bottom":
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif axis == "left right":
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        new_img = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        return new_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    
    def invert(self, image: Image.Image) -> Image.Image:
        if image.mode == "RGBA":
            r, g, b, a = image.split()
            rgb = Image.merge("RGB", (r, g, b))
            inverted = Image.eval(rgb, lambda x: 255 - x)
            inverted.putalpha(a)
            return inverted
        return Image.eval(image, lambda x: 255 - x)
    
    def pixelate(self, image: Image.Image, pixel_size: int = 10) -> Image.Image:
        small = image.resize(
            (image.width // pixel_size, image.height // pixel_size),
            resample=Image.Resampling.BILINEAR
        )
        return small.resize(image.size, Image.Resampling.NEAREST)
    
    def edge_detect(self, image: Image.Image) -> Image.Image:
        if image.mode == "RGBA":
            alpha = image.split()[3]
            rgb = image.convert("RGB").filter(ImageFilter.FIND_EDGES)
            rgb.putalpha(alpha)
            return rgb
        return image.filter(ImageFilter.FIND_EDGES)
    
    def deepfry(self, image: Image.Image) -> Image.Image:
        img = image.copy().convert("RGB")

        # Boost saturation aggressively
        img = ImageEnhance.Color(img).enhance(3.0)

        # Blow out the contrast and brightness
        img = ImageEnhance.Contrast(img).enhance(3.0)
        img = ImageEnhance.Brightness(img).enhance(1.2)

        # Sharpen multiple times for that crunchy look
        for _ in range(5):
            img = img.filter(ImageFilter.SHARPEN)

        # Simulate JPEG compression artifacts by round-tripping through low quality JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=10)
        buffer.seek(0)
        img = Image.open(buffer).copy()

        return img
    def rainbowify(self, image: Image.Image) -> Image.Image:
        img = image.copy().convert("RGBA")
        width, height = img.size
        
        # Create a rainbow gradient
        gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        
        for y in range(height):
            r = int(255 * (y / height))
            g = int(255 * ((height - y) / height))
            b = 128
            draw.line([(0, y), (width, y)], fill=(r, g, b, 128))
        
        # Overlay the gradient onto the original image
        return Image.alpha_composite(img, gradient)

    def sepia(self, image: Image.Image) -> Image.Image:
        alpha = image.split()[3] if image.mode == "RGBA" else None
        img = image.convert("RGB")
        
        r, g, b = img.split()
        new_r = r.point(lambda x: min(255, int(x * 0.393 + x * 0.769 + x * 0.189)))
        new_g = g.point(lambda x: min(255, int(x * 0.349 + x * 0.686 + x * 0.168)))
        new_b = b.point(lambda x: min(255, int(x * 0.272 + x * 0.534 + x * 0.131)))
        
        result = Image.merge("RGB", (new_r, new_g, new_b))
        if alpha:
            result.putalpha(alpha)
        return result

    def emboss(self, image: Image.Image) -> Image.Image:
        return image.filter(ImageFilter.EMBOSS)
    
    def solarize(self, image: Image.Image, threshold: int = 128) -> Image.Image:
        if image.mode == "RGBA":
            alpha = image.split()[3]
            rgb = image.convert("RGB").point(lambda x: 255 - x if x < threshold else x)
            rgb.putalpha(alpha)
            return rgb
        return image.point(lambda x: 255 - x if x < threshold else x)
    
    def posterize(self, image: Image.Image, bits: int = 4) -> Image.Image:
        if image.mode == "RGBA":
            alpha = image.split()[3]
            rgb = image.convert("RGB").point(lambda x: (x >> (8 - bits)) << (8 - bits))
            rgb.putalpha(alpha)
            return rgb
        return image.point(lambda x: (x >> (8 - bits)) << (8 - bits))
    
    def glitch(self, image: Image.Image) -> Image.Image:
        img = image.copy().convert("RGBA")
        width, height = img.size
        
        for _ in range(60):
            y1 = random.randint(0, height - 1)
            slice_height = random.randint(5, 40)
            y2 = min(y1 + slice_height, height)
            
            shift_x = random.randint(-150, 150)
            
            strip = img.crop((0, y1, width, y2))
            
            # wrap the strip around instead of going out of bounds
            if shift_x >= 0:
                visible = strip.crop((0, 0, width - shift_x, y2 - y1))
                img.paste(visible, (shift_x, y1))
            else:
                visible = strip.crop((-shift_x, 0, width, y2 - y1))
                img.paste(visible, (0, y1))
        
        return img

    def swirl(self, image: Image.Image, strength: float = 1.0) -> Image.Image:
        img = image.copy().convert("RGBA")
        width, height = img.size
        center_x, center_y = width / 2, height / 2
        
        pixels = img.load()
        
        for x in range(width):
            for y in range(height):
                dx = x - center_x
                dy = y - center_y
                distance = (dx**2 + dy**2) ** 0.5
                
                if distance > 0:
                    angle = strength * distance / max(center_x, center_y)
                    cos_angle = math.cos(angle)
                    sin_angle = math.sin(angle)
                    
                    new_x = int(center_x + cos_angle * dx - sin_angle * dy)
                    new_y = int(center_y + sin_angle * dx + cos_angle * dy)
                    
                    if 0 <= new_x < width and 0 <= new_y < height:
                        pixels[x, y] = img.getpixel((new_x, new_y))
        
        return img


@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class ImageCommands(app_commands.Group):
    """Group of image-related commands."""
    def __init__(self):
        super().__init__(
            name="image",
            description="Commands for generating and manipulating images."
        )

    img_gen = ImageGenerator(ROOT_DIR)

    async def fetch_image(self, source) -> Image.Image:
        url = source.url if isinstance(source, discord.Attachment) else source
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                image_bytes = await resp.read()
        return Image.open(BytesIO(image_bytes)).convert("RGBA")

    async def resolve_image(self, image, url):
        if image:
            return await self.fetch_image(image)
        elif url:
            return await self.fetch_image(url)
        return None

    async def send_image(
        self,
        interaction: discord.Interaction,
        image: Image.Image,
        filename: str = "image.png"
    ):
        with io.BytesIO() as buffer:
            image.save(buffer, format="PNG")
            buffer.seek(0)
            file = discord.File(fp=buffer, filename=filename)
            await interaction.followup.send(file=file)

    async def run_image_command(self, interaction: discord.Interaction, func, image=None, url=None):
        if image is None and url is None:
            await interaction.response.send_message("please provide an image or a url!", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await func()
        except Exception as e:
            await interaction.followup.send(f"An error occurred:\n```\n{e}\n```")

    @app_commands.command(name="wanted", description="Create a wanted poster!")
    @app_commands.describe(
        user="The criminal you want the poster for.",
        amount="The bounty amount."
    )
    async def wanted(self, interaction: discord.Interaction, user: discord.User, amount: int):
        async def logic():
            output_bytes = await self.img_gen.create_wanted_poster(user, amount)
            file = discord.File(output_bytes, filename=f"wanted_{user.name}.png")
            await interaction.followup.send(file=file)
        await self.run_image_command(interaction, logic)

    @app_commands.command(name="misquote", description="Create a fake quote image")
    @app_commands.describe(
        message="What did they say?",
        user="Who said it?"
    )
    async def misquote(self, interaction: discord.Interaction, user: discord.User, message: str):
        async def logic():
            output_bytes = await self.img_gen.create_quote_image(user, message)
            file = discord.File(output_bytes, filename=f"quote_{user.name}.png")
            await interaction.followup.send(file=file)
        await self.run_image_command(interaction, logic)

    @app_commands.command(name="rarch", description="Generate an inkblot image")
    async def rarch(self, interaction: discord.Interaction):
        inkblot_image = self.img_gen.generate_inkblot()
        with io.BytesIO() as image_binary:
            inkblot_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename='inkblot.png')
            embed = discord.Embed(title="What do you see?")
            embed.set_image(url="attachment://inkblot.png")
            await interaction.response.send_message(embed=embed, file=file)

    @app_commands.command(name="caption", description="Add a caption to an image")
    @app_commands.describe(
        caption="The caption text to add to the image.",
        image="The image to caption.",
        url="Or provide an image URL instead."
    )
    async def caption(self, interaction: discord.Interaction, caption: str, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.caption_image(img, caption)
            await self.send_image(interaction, result, "caption.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="meme", description="Apply a meme-style filter to an image")
    @app_commands.describe(
        caption="The caption text to add to the image.",
        image="The image to memeify.",
        url="Or provide an image URL instead.",
        bottom="Whether to place the caption at the bottom (default is top)."
    )
    async def meme(self, interaction: discord.Interaction, caption: str, image: discord.Attachment = None, url: str = None, bottom: bool = False):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.memeify_image(img, bottom, caption)
            await self.send_image(interaction, result, "meme.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="grayscale", description="Convert an image to grayscale")
    @app_commands.describe(
        image="The image to convert to grayscale.",
        url="Or provide an image URL instead."
    )
    async def grayscale(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.grayscale(img)
            await self.send_image(interaction, result, "gray.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="blur", description="Apply a blur effect to an image")
    @app_commands.describe(
        image="The image to blur.",
        url="Or provide an image URL instead."
    )
    async def blur(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.blur(img)
            await self.send_image(interaction, result, "blur.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="rotate", description="Rotate an image by a specified angle")
    @app_commands.describe(
        image="The image to rotate.",
        url="Or provide an image URL instead.",
        angle="The angle to rotate the image"
    )
    async def rotate(self, interaction: discord.Interaction, angle: Literal[90, 180, 360], image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.rotate(img, angle)
            await self.send_image(interaction, result, "rotate.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="flip", description="Flip an image along a specified axis")
    @app_commands.describe(
        image="The image to flip.",
        url="Or provide an image URL instead.",
        axis="The axis to flip the image (top bottom, left right, or both)."
    )
    async def flip(self, interaction: discord.Interaction, axis: Literal["top bottom", "left right", "both"], image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.flip(img, axis)
            await self.send_image(interaction, result, "flip.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="invert", description="Invert the colors of an image")
    @app_commands.describe(
        image="The image to invert.",
        url="Or provide an image URL instead."
    )
    async def invert(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.invert(img)
            await self.send_image(interaction, result, "invert.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="pixelate", description="Pixelate an image")
    @app_commands.describe(
        image="The image to pixelate.",
        url="Or provide an image URL instead."
    )
    async def pixelate(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.pixelate(img)
            await self.send_image(interaction, result, "pixelate.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="deepfry", description="Apply a deep fry effect to an image")
    @app_commands.describe(
        image="The image to deep fry.",
        url="Or provide an image URL instead."
    )
    async def deepfry(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.deepfry(img)
            await self.send_image(interaction, result, "deepfry.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="edgedetect", description="Apply an edge detection filter to an image")
    @app_commands.describe(
        image="The image to apply edge detection to.",
        url="Or provide an image URL instead."
    )
    async def edgedetect(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.edge_detect(img)
            await self.send_image(interaction, result, "edges.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="rainbow", description="Overlay a rainbow gradient onto an image")
    @app_commands.describe(
        image="The image to rainbowify.",
        url="Or provide an image URL instead."
    )
    async def rainbow(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.rainbowify(img)
            await self.send_image(interaction, result, "rainbow.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="sepia", description="Apply a sepia tone to an image")
    @app_commands.describe(
        image="The image to sepia-ize.",
        url="Or provide an image URL instead."
    )
    async def sepia(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.sepia(img)
            await self.send_image(interaction, result, "sepia.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="emboss", description="Apply an emboss effect to an image")
    @app_commands.describe(
        image="The image to emboss.",
        url="Or provide an image URL instead."
    )
    async def emboss(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.emboss(img)
            await self.send_image(interaction, result, "emboss.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="solarize", description="Apply a solarize effect to an image")
    @app_commands.describe(
        image="The image to solarize.",
        url="Or provide an image URL instead."
    )
    async def solarize(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.solarize(img)
            await self.send_image(interaction, result, "solarize.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="posterize", description="Apply a posterize effect to an image")
    @app_commands.describe(
        image="The image to posterize.",
        url="Or provide an image URL instead."
    )
    async def posterize(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.posterize(img)
            await self.send_image(interaction, result, "posterize.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="glitch", description="Apply a glitch effect to an image")
    @app_commands.describe(
        image="The image to glitch.",
        url="Or provide an image URL instead."
    )
    async def glitch(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.glitch(img)
            await self.send_image(interaction, result, "glitch.png")
        await self.run_image_command(interaction, logic, image, url)

    @app_commands.command(name="swirl", description="Apply a swirl effect to an image")
    @app_commands.describe(
        image="The image to swirl.",
        url="Or provide an image URL instead."
    )
    async def swirl(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        async def logic():
            img = await self.resolve_image(image, url)
            result = self.img_gen.swirl(img)
            await self.send_image(interaction, result, "swirl.png")
        await self.run_image_command(interaction, logic, image, url)


async def image_setup(bot):
    bot.tree.add_command(ImageCommands())
