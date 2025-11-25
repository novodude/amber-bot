import discord
from discord import app_commands
import random
import aiohttp
import asyncio
import json
import os


async def animals_setup(bot):
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

