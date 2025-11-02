from PIL import Image, ImageDraw
import random
import io
import discord
from discord import app_commands


def generate_inkblot(width=500, height=700):
    half_width = width // 2
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    num_blobs = random.randint(10, 25)
    
    for _ in range(num_blobs):
        x = random.randint(0, half_width - 50)
        y = random.randint(50, height - 50)
        
        width_size = random.randint(30, 180)
        height_size = random.randint(30, 180)
        
        shape_type = random.choice(['ellipse', 'ellipse', 'polygon', 'irregular'])
        
        if shape_type == 'ellipse':
            draw.ellipse([x, y, x + width_size, y + height_size], fill='black')
        
        elif shape_type == 'polygon':
            points = []
            num_points = random.randint(5, 9)
            center_x = x + width_size // 2
            center_y = y + height_size // 2
            
            for angle in range(0, 360, 360 // num_points):
                radius = random.randint(20, 100)
                px = center_x + int(radius * random.uniform(0.7, 1.3) * (angle / 360))
                py = center_y + int(radius * random.uniform(0.7, 1.3) * (angle / 360))
                points.append((px, py))
            
            if len(points) >= 3:
                draw.polygon(points, fill='black')
        
        else:
            num_circles = random.randint(3, 7)
            for _ in range(num_circles):
                offset_x = random.randint(-30, 30)
                offset_y = random.randint(-30, 30)
                circle_size = random.randint(20, 80)
                draw.ellipse(
                    [x + offset_x, y + offset_y, 
                     x + offset_x + circle_size, y + offset_y + circle_size],
                    fill='black'
                )
        
        if random.random() > 0.4:
            num_splatters = random.randint(5, 15)
            for _ in range(num_splatters):
                splatter_x = x + random.randint(-40, width_size + 40)
                splatter_y = y + random.randint(-40, height_size + 40)
                splatter_size = random.randint(3, 12)
                draw.ellipse(
                    [splatter_x, splatter_y, 
                     splatter_x + splatter_size, splatter_y + splatter_size],
                    fill='black'
                )
    
    for _ in range(random.randint(3, 8)):
        start_x = random.randint(0, half_width)
        start_y = random.randint(50, height - 50)
        end_x = random.randint(0, half_width)
        end_y = random.randint(50, height - 50)
        width_line = random.randint(8, 25)
        draw.line([(start_x, start_y), (end_x, end_y)], fill='black', width=width_line)
    
    for _ in range(random.randint(100, 300)):
        noise_x = random.randint(0, half_width)
        noise_y = random.randint(0, height)
        noise_size = random.randint(1, 3)
        draw.ellipse(
            [noise_x, noise_y, noise_x + noise_size, noise_y + noise_size],
            fill='black'
        )
    
    left_half = img.crop((0, 0, half_width, height))
    right_half = left_half.transpose(Image.FLIP_LEFT_RIGHT)
    img.paste(right_half, (half_width, 0))
    
    return img

async def inkblot_setup(bot):
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
