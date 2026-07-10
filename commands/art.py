import discord
from discord import app_commands
from utils.art.art import ArtUtils
import io

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Art(app_commands.Group):
    """Commands related to art."""

    def __init__(self):
        super().__init__(name="art", description="Commands related to art.")
        self.art_utils = ArtUtils()

    @app_commands.command(name="oc_maker", description="Generate a random OC character card.")
    @app_commands.describe(
        name="Character name",
        age="Exact age (overrides age range)",
        min_age="Minimum age (default 18)",
        max_age="Maximum age (default 60)",
        color="Base hex color e.g. #a832f5"
    )
    async def oc_maker(
        self,
        interaction: discord.Interaction,
        name: str | None,
        age: int | None,
        color: str | None,
        min_age: int = 18,
        max_age: int = 60
    ):

        if min_age < 0 or max_age < 0:
            await interaction.response.send_message("Age cannot be negative.", ephemeral=True)
            return

        if min_age > max_age:
            await interaction.response.send_message("Minimum age cannot be greater than maximum age.", ephemeral=True)
            return

        if max_age > 9999:
            await interaction.response.send_message("Maximum age cannot be greater than 9999.", ephemeral=True)
            return

        await interaction.response.defer()

        image = await self.art_utils.get_character_image(
            base_image_path="assets/art/art_template.png",
            name=name,
            age=age,
            min_age=min_age,
            max_age=max_age,
            base_color=color
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await interaction.followup.send(file=discord.File(buffer, filename="character.png"))

    @app_commands.command(name="color_scheme", description="Generate a color scheme based on a base color.")
    @app_commands.describe(amount="how many colors you want?")
    async def color_scheme(self, interaction: discord.Interaction, amount: int = 5):
        if amount > 25:
            await interaction.response.send_message("You can only generate up to 25 colors at a time.", ephemeral=True)
            return

        await interaction.response.defer()

        image, color_scheme = await self.art_utils.get_color_scheme_image(amount)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        color_text = "\n".join(color_scheme)

        embed = discord.Embed(title="Color Scheme", description=f"Generated {amount} colors.\n{color_text}", color=0x2F3136)

        await interaction.followup.send(embed=embed, file=discord.File(buffer, filename="color_scheme.png"))


    @app_commands.command(name="pose", description="get a random pose for your character")
    async def pose(self, interaction: discord.Interaction):
        await interaction.response.defer()

        image = await self.art_utils.get_character_pose()

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await interaction.followup.send("here's a idea have fun drawing!", file=discord.File(buffer, filename="pose.png"))

class Generators(app_commands.Group):
    """Commands related to generators."""

    def __init__(self):
        super().__init__(name="generate", description="Commands related to generators.")
        self.art_utils = ArtUtils()

    @app_commands.command(name="traits", description="get random traits for your character")
    @app_commands.describe(amount="how many traits you want?")
    async def traits_generator(self, interaction: discord.Interaction, amount: int = 4):
        if amount > 25:
            await interaction.response.send_message("You can only generate up to 25 traits at a time.", ephemeral=True)
            return

        await interaction.response.defer()

        traits_data = await self.art_utils.generate_character_traits(amount)

        trait_text = "\n".join([f"{i+1}. {trait}" for i, (_, trait) in enumerate(traits_data)])

        embed = discord.Embed(title="Character Traits", description=f"Generated {amount} traits.\n{trait_text}", color=0x2F3136)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="name", description="Generate a random name for your character.")
    async def name_generator(self, interaction: discord.Interaction):
        await interaction.response.defer()

        name = await self.art_utils.generate_character_name()

        embed = discord.Embed(title="Character Name", description=f"Generated name: {name}", color=0x2F3136)

        await interaction.followup.send(embed=embed)


async def art_setup(bot):
    bot.tree.add_command(Art())
    bot.tree.add_command(Generators())
