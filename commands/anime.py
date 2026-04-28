import discord
from discord import app_commands
import aiohttp

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Anime(app_commands.Group):
    """Commands related to anime."""
    
    def __init__(self):
        super().__init__(name="anime", description="Commands related to anime.")


    async def get_anime_image(self, type: str):
        url = f"https://nekos.best/api/v2/{type}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return "Sorry, I couldn't fetch an image at the moment. Please try again later."
            except Exception as e:
                return e

    async def get_anime_quote(self):
        url = "https://yurippe.vercel.app/api/quotes?random=1"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        return data[0]  # returns a list
                    else:
                        return "Sorry, I couldn't fetch a quote at the moment. Please try again later."
            except Exception as e:
                return e

    def build_embed(self, data: dict, title: str):
        image_url = data['results'][0]['url']
        embed = discord.Embed(title=title, color=discord.Color.purple())
        embed.add_field(name="Source", value=f"[Artist's Page]({data['results'][0]['artist_href']}) | [Artwork]({data['results'][0]['source_url']})", inline=False)
        embed.set_image(url=image_url)
        embed.set_footer(text=f"Artist: {data['results'][0]['artist_name']} | Dimensions: {data['results'][0]['dimensions']['width']}x{data['results'][0]['dimensions']['height']}")
        return embed


    @app_commands.command(name="waifu", description="Get a random anime waifu image.")
    async def waifu(self, interaction: discord.Interaction):
        await interaction.response.defer()
        image_url = await self.get_anime_image(type="waifu")
        if image_url:
            embed = self.build_embed(image_url, title="Here's a random waifu for you!")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch a waifu image at the moment. Please try again later.")

    @app_commands.command(name="husbando", description="Get a random anime husbando image.")
    async def husbando(self, interaction: discord.Interaction):
        await interaction.response.defer()
        image_url = await self.get_anime_image(type="husbando")
        if image_url:
            embed = self.build_embed(image_url, title="Here's a random husbando for you!")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch a husbando image at the moment. Please try again later.")

    @app_commands.command(name="neko", description="Get a random anime neko image.")
    async def neko(self, interaction: discord.Interaction):
        await interaction.response.defer()
        image_url = await self.get_anime_image(type="neko")
        if image_url:
            embed = self.build_embed(image_url, title="Here's a random neko for you!")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch a neko image at the moment. Please try again later.")

    @app_commands.command(name="kitsune", description="Get a random anime kitsune image.")
    async def kitsune(self, interaction: discord.Interaction):
        await interaction.response.defer()
        image_url = await self.get_anime_image(type="kitsune")
        if image_url:
            embed = self.build_embed(image_url, title="Here's a random kitsune for you!")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch a kitsune image at the moment. Please try again later.")

    @app_commands.command(name="quote", description="Get a random anime quote.")
    async def quote(self, interaction: discord.Interaction):
        await interaction.response.defer()
        quote_data = await self.get_anime_quote()
        if quote_data:
            embed = discord.Embed(
                title="Here's a random anime quote for you!",
                description=f"\"{quote_data['quote']}\"\n\n- {quote_data['character']} from {quote_data['show']}",
                color=discord.Color.purple()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch an anime quote at the moment. Please try again later.")





async def anime_setup(bot):
    bot.tree.add_command(Anime())
