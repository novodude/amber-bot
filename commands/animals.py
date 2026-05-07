from os import replace
import random
import aiohttp
import discord
from discord import app_commands
import dotenv

api_key = dotenv.get_key(".env", "GIPHY_API")


SRA_BASE = "https://some-random-api.com/animal"
ANIMALITY_BASE = "https://api.animality.xyz/all"


STUMMI_SHEEP_ART = [
    "https://cdn.discordapp.com/attachments/1403112075005530143/1499042413375782983/Untitled181_20260429093859.png?ex=69fde78a&is=69fc960a&hm=1ee7f73fa1c2f36d494a99b3db4d67e28060e587ca9fe0c0105609c629d503b5&",
    "https://cdn.discordapp.com/attachments/1403112075005530143/1490521124646424766/Screenshot_20260405_211633_ibisPaint_X.jpg?ex=69fde2b8&is=69fc9138&hm=ec097826ab881aa276cf201f660079d0d4668fa04997478ef2a46e4c98637064&",
    "https://cdn.discordapp.com/attachments/1403112075005530143/1488422441012297849/Untitled155_20260331021858.png?ex=69fd806b&is=69fc2eeb&hm=f30e2e83e02894a324455394ef81e2251d8189ec73293a99e7402d8345ee3d1c&",
    "https://cdn.discordapp.com/attachments/1403112075005530143/1488422441590980718/Untitled155_20260331021902.png?ex=69fd806b&is=69fc2eeb&hm=25188b190f3bcbf09807bd67eb26a400cfc5a22e5dc67dd6719466ca895adb29&",
    "https://cdn.discordapp.com/attachments/1403112075005530143/1486187965293138121/Untitled148_20260324221932.png?ex=69fd4866&is=69fbf6e6&hm=e03ee79ad495cd85c0986be46c320cb1085a179d01aac3db1baa3a79bc809d78&",
    "https://cdn.discordapp.com/attachments/1403112075005530143/1486212539564949625/Untitled148_20260324235031.png?ex=69fd5f49&is=69fc0dc9&hm=99473e1bc14ca12ebee4537047ca25b0c5fa4c70d077a5fce3bdcb86e53f703d&"
]

STUMMI_CHANCE = 0.1

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class AnimalCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="animal",
            description="Get random animal images and facts",
            guild_only=False
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    async def _send_animal(
        self,
        interaction: discord.Interaction,
        *,
        title: str,
        image_url: str,
        fact: str | None = None,
        color: discord.Color = discord.Color.green(),
    ):
        embed = discord.Embed(title=title, description=fact, color=color)
        embed.set_image(url=image_url)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    async def _error(self, interaction: discord.Interaction, e: Exception):
        embed = discord.Embed(
            title="Error",
            description=f"```\n{e}\n```",
            color=discord.Color.red(),
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    async def _fetch_sra(self, session: aiohttp.ClientSession, animal: str):
        """Fetch from some-random-api.com — returns (image_url, fact)."""
        async with session.get(f"{SRA_BASE}/{animal}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["image"], data.get("fact")

    async def _fetch_animality(self, session: aiohttp.ClientSession, animal: str):
        """Fetch from animality.xyz — returns (image_url, fact)."""
        async with session.get(f"{ANIMALITY_BASE}/{animal}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["image"], data.get("fact")


    @app_commands.command(name="duck", description="Get a random duck image")
    async def duck(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://random-d.uk/api/v2/list") as resp:
                    data = await resp.json()
                    gifs = data.get("gifs", [])
                    gif_url = (
                        f"https://random-d.uk/api/{random.choice(gifs)}"
                        if gifs
                        else "https://random-d.uk/api/random"
                    )
            await self._send_animal(interaction, title="🦆 Random Duck!", image_url=gif_url)
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="rotta", description="Get a random rat gif")
    async def rat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rat_url = f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=rat&rating=G"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(rat_url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    gif_url = data["data"]["images"]["original"]["url"]
            await self._send_animal(
                interaction, title="🐀 Random Rat!", image_url=gif_url,
                color=discord.Color.dark_green()
            )
        except Exception as e:
            e = str(e).replace(api_key, "[REDACTED]")
            await self._error(interaction, e)

    @app_commands.command(name="sheep", description="Get a random sheep gif")
    async def sheep(self, interaction: discord.Interaction):
        colors = [discord.Color.orange(), discord.Color.from_rgb(255, 255, 255),
                  discord.Color.pink(), discord.Color.from_rgb(0, 0, 0)]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=sheep") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    gif_url = data["data"]["images"]["original"]["url"]
            
            if random.random() < STUMMI_CHANCE:
                url = random.choice(STUMMI_SHEEP_ART)
            else:
                url = gif_url

            await self._send_animal(
                interaction, title="🐑 Random Sheep!", image_url=url,
                color=random.choice(colors)
            )
        except Exception as e:
            e = str(e).replace(api_key, "[REDACTED]")
            await self._error(interaction, e)

    @app_commands.command(name="cat", description="Get a random cat gif")
    async def cat(self, interaction: discord.Interaction):
        colors = [discord.Color.orange(), discord.Color.from_rgb(255, 255, 255),
                  discord.Color.pink(), discord.Color.from_rgb(0, 0, 0)]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.thecatapi.com/v1/images/search?mime_types=gif") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    gif_url = data[0]["url"]
                async with session.get("https://meowfacts.herokuapp.com/") as resp:
                    fact = (await resp.json())["data"][0] if resp.status == 200 else None
            await self._send_animal(
                interaction, title="🐱 Random Cat!", image_url=gif_url,
                fact=fact, color=random.choice(colors)
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="dog", description="Get a random dog gif")
    async def dog(self, interaction: discord.Interaction):
        colors = [discord.Color.orange(), discord.Color.from_rgb(255, 255, 255),
                  discord.Color.pink(), discord.Color.from_rgb(0, 0, 0)]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.thedogapi.com/v1/images/search?mime_types=gif") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    gif_url = data[0]["url"]
            await self._send_animal(
                interaction, title="🐶 Random Dog!", image_url=gif_url,
                color=random.choice(colors)
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="fox", description="Get a random fox image")
    async def fox(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://randomfox.ca/floof/") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    image_url = data["image"]
            await self._send_animal(
                interaction, title="🦊 Random Fox!", image_url=image_url,
                color=discord.Color.orange()
            )
        except Exception as e:
            await self._error(interaction, e)


    @app_commands.command(name="bird", description="Get a random bird image with a fact")
    async def bird(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                image_url, fact = await self._fetch_sra(session, "bird")
            await self._send_animal(
                interaction, title="🐦 Random Bird!", image_url=image_url,
                fact=fact, color=discord.Color.blue()
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="panda", description="Get a random panda image with a fact")
    async def panda(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                image_url, fact = await self._fetch_sra(session, "panda")
            await self._send_animal(
                interaction, title="🐼 Random Panda!", image_url=image_url,
                fact=fact, color=discord.Color.dark_green()
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="redpanda", description="Get a random red panda image with a fact")
    async def redpanda(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                image_url, fact = await self._fetch_sra(session, "red_panda")
            await self._send_animal(
                interaction, title="🦊 Random Red Panda!", image_url=image_url,
                fact=fact, color=discord.Color.red()
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="koala", description="Get a random koala image with a fact")
    async def koala(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                image_url, fact = await self._fetch_sra(session, "koala")
            await self._send_animal(
                interaction, title="🐨 Random Koala!", image_url=image_url,
                fact=fact, color=discord.Color.greyple()
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="kangaroo", description="Get a random kangaroo image with a fact")
    async def kangaroo(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session:
                image_url, fact = await self._fetch_sra(session, "kangaroo")
            await self._send_animal(
                interaction, title="🦘 Random Kangaroo!", image_url=image_url,
                fact=fact, color=discord.Color.from_rgb(205, 133, 63)
            )
        except Exception as e:
            await self._error(interaction, e)

    @app_commands.command(name="bunny", description="Get a random bunny image")
    async def bunny(self, interaction: discord.Interaction):
        # bunnies.io — returns { media: { gif, poster } }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.bunnies.io/v2/loop/random/?media=gif,png") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    image_url = data["media"]["gif"] or data["media"]["poster"]
            await self._send_animal(
                interaction, title="🐰 Random Bunny!", image_url=image_url,
                color=discord.Color.from_rgb(255, 182, 193)
            )
        except Exception as e:
            await self._error(interaction, e)

async def animal_setup(bot):
    bot.tree.add_command(AnimalCommands())
