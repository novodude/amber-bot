from PIL import Image, ImageDraw, ImageFilter
import random
import io
import discord
from discord import app_commands


def generate_inkblot(width=500, height=700):
    half_width = width // 2
    random_color = ['white', 'honeydew','black', '#432323', '#0C2B4E', "#7A2828"]
    bg_color = random.choice(random_color)
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    dark = ['black', '#432323', '#0C2B4E', '#7A2828', 'darkblue', 'darkred']
    light = ['white', 'honeydew', 'lightpink', 'lightblue', 'lightyellow']

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

    img = img.filter(ImageFilter.GaussianBlur(radius=1.1))
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
