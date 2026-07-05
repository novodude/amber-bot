import random
from utils.art.assets import TRAITS, ITEMS, FONTS, NAMES, POSES
from PIL import Image, ImageDraw, ImageFont



class ArtUtils:

    async def get_random_color(self):
        return random.randint(0, 0xFFFFFF)
        

    async def create_color_scheme(self, base_color: int | None, amount: int = 5):
        scheme = []
        if base_color is None:
            base_color = await self.get_random_color()
        while len(scheme) < amount:
            new_color = base_color * random.uniform(0.8, 1.2)
            new_color = max(0, min(0xFFFFFF, int(new_color)))
            if f"#{new_color:06x}" not in scheme:
                scheme.append(f"#{new_color:06x}")
        return scheme


    async def generate_character_traits(self, amount: int = 4):
        traits = []
        trait_types = list(TRAITS.keys())
        for index in range(amount):
            trait_type = trait_types[index % len(trait_types)]
            trait = random.choice(TRAITS[trait_type])
            traits.append((trait_type, trait))
        return traits

    async def generate_character_items(self):
        items = {}
        for item_type, item_list in ITEMS.items():
            image = Image.open(random.choice(item_list))
            image = image.crop(image.getbbox())
            items[item_type] = image
        return items
        

    async def generate_character_name(self):
        first_name = random.choice(NAMES)
        last_name = random.choice(NAMES)
        return f"{first_name} {last_name}"

    async def pick_font(self):
        return random.choice(FONTS)

    async def generate_character_age(self, min_age: int | None, max_age: int | None):
        return random.randint(min_age if min_age else 18, max_age if max_age else 60)

    async def generate_character_pronunce(self):
        pronouns = [
            "he/him", "she/her", "they/them", "ze/zir",
            "xe/xem", "fae/faer", "ey/em", "ve/ver", "per/per", "it/its"
        ]
        return random.choice(pronouns)

    async def hex_to_int(self, hex_color: str):
        return int(hex_color.lstrip("#"), 16)

    async def tent_template(self, image: Image.Image, base_color: int | None = None):
        if base_color is None:
            base_color = await self.get_random_color()

        image = image.convert("RGBA")
        width, height = image.size

        # tent the image by applying a color overlay
        overlay = Image.new("RGBA", (width, height), (base_color >> 16 & 0xFF, base_color >> 8 & 0xFF, base_color & 0xFF, 128))
        image = Image.alpha_composite(image, overlay)

        return image

    async def put_text_on_image(self, image: Image.Image, text: str, font_path: str, color_scheme: list[str], position: tuple[int, int], stroke_fill: str | None,  fill: str | None, stroke_width: int = 2, font_size: int = 64):

        image = image.convert("RGBA")

        font = ImageFont.truetype(font_path, font_size)

        draw = ImageDraw.Draw(image)

        if stroke_fill is None:
            stroke_fill = color_scheme[4]
        if fill is None:
            fill = color_scheme[3]


        draw.text(position, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)

        return image

    async def put_item_on_image(self, image: Image.Image, item_image: Image.Image, position: tuple[int, int], scale: float = 0.5):
        image = image.convert("RGBA")
        item_image = item_image.convert("RGBA")

        item_width, item_height = item_image.size
        new_size = (int(item_width * scale), int(item_height * scale))
        item_image = item_image.resize(new_size, 1)

        image.paste(item_image, position, item_image)

        return image

    async def put_color_scheme_on_image(self, image: Image.Image, color_scheme: list[str]):
        image = image.convert("RGBA")
        width, height = image.size

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # bboxes measured directly from art_template.png
        circles = [
            (138, 1493, 370, 1725),  # top-left
            (429, 1493, 661, 1725),  # top-right
            (332, 1687, 467, 1821),  # center
            (138, 1781, 370, 2013),  # bottom-left
            (429, 1781, 661, 2013),  # bottom-right
        ]

        for i, color in enumerate(color_scheme):
            draw.ellipse(circles[i], fill=color)

        image = Image.alpha_composite(image, overlay)
        return image


    async def get_color_scheme_image(self, amount: int = 5):
        base_color = await self.get_random_color()
        color_scheme = await self.create_color_scheme(base_color, amount)

        image = Image.new("RGBA", (160 * amount, 200), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)

        for i, color in enumerate(color_scheme):
            draw.rectangle([i * 160, 0, (i + 1) * 160, 200], fill=color)

        return image, color_scheme

    async def get_character_image(self, base_image_path: str, prononuce: str | None = None, base_color: str | int | None = None, name: str | None = None, age: int | None = None, min_age: int | None = None, max_age: int | None = None):
        image = Image.open(base_image_path).convert("RGBA")
        
        if base_color is None:
            base_color = await self.get_random_color()
        else:
            base_color = await self.hex_to_int(base_color)

        inverted_color = base_color ^ 0xFFFFFF
        inverted_hex = f"#{inverted_color:06x}"

        color_scheme = await self.create_color_scheme(base_color)
        
        image = await self.tent_template(image, base_color)
        
        if name is None:
            name = await self.generate_character_name()
        if age is None:
            age = await self.generate_character_age(min_age, max_age)
        if prononuce is None:
            prononuce = await self.generate_character_pronunce()
        
        primary_font = await self.pick_font()
        secondary_font = await self.pick_font()

        items = await self.generate_character_items()

        traits = await self.generate_character_traits()

        image = await self.put_text_on_image(
            image, f"{name}", primary_font, color_scheme,
            position=(180, 95), stroke_fill=None, fill=inverted_hex
        )
        image = await self.put_text_on_image(
            image, f"Age: {age}", primary_font, color_scheme,
            position=(230, 220), stroke_fill=None, fill=inverted_hex
        )
        image = await self.put_text_on_image(
            image, f"Pronouns: {prononuce}", primary_font, color_scheme,
            position=(270, 345), stroke_fill=None, fill=inverted_hex, font_size=43
        )

        FLOWER_SIZE = 193  # 173px flower + 20px padding

        item_centers = [
            (399, 690),   # hat
            (399, 952),   # top
            (631, 864),   # shoes
            (166, 864),   # accessory  
            (399, 1213),  # bottom
        ]

        for index, (_, item_image) in enumerate(items.items()):
            cx, cy = item_centers[index]
            # scale to target size preserving aspect ratio
            w, h = item_image.size
            scale = FLOWER_SIZE / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            item_image = item_image.resize((new_w, new_h), Image.LANCZOS)
            # center on flower
            pos = (cx - new_w // 2, cy - new_h // 2)
            image = await self.put_item_on_image(image, item_image, pos, scale=1.0)

        image = await self.put_color_scheme_on_image(image, color_scheme)
        
        traits_coords = [
            (130, 2185),   # top-left (next to top-left asterisk)
            (470, 2185),   # top-right
            (130, 2359),   # bottom-left
            (470, 2359),   # bottom-right
        ]

        for index, (_, trait) in enumerate(traits):
            image = await self.put_text_on_image(
                image, trait, secondary_font, color_scheme,
                position=traits_coords[index], stroke_fill=None, fill=inverted_hex, font_size=28
            )
        return image

    async def get_character_pose(self):
        image = Image.open(random.choice(POSES)).convert("RGBA")
        return image

