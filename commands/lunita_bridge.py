import random
import statistics
import discord
from discord.ext import commands
from typing import Optional

from utils.reactions import ACTIONS, REACTIONS, build_embed, build_title, build_counter_text
from utils.action_counts import (
    increment_action_count, get_received_count, get_given_count,
    get_action_between_users, maybe_reward_dabloons,
)
from utils.userbase.ensure_registered import ensure_registered


async def setup_lunita_bridge(bot: commands.Bot):

    @bot.command(name="do")
    async def do_action(ctx: commands.Context, action: str, user: Optional[discord.Member] = None):
        action = action.lower()
        if action not in ACTIONS:
            return  # silently ignore — not a real action, don't spam the channel

        await ensure_registered(ctx.author.id, ctx.author.display_name)
        action_data = ACTIONS[action]
        author = ctx.author
        everyone = user is None and "everyone" in ctx.message.content.lower()

        if everyone:
            base_desc = random.choice(action_data['desc_everyone']).format(user=author, author=author)
        elif user and user.id == author.id:
            base_desc = random.choice(action_data['desc_self']).format(user=author, author=author)
        elif user:
            base_desc = random.choice(action_data['desc_other']).format(user=user, author=author)
        else:
            base_desc = random.choice(action_data['desc_self']).format(user=author, author=author)

        title = build_title(action, action_data, author.display_name, user.display_name if user else None, everyone)

        counter = ""
        if not everyone:
            target = user or author
            await increment_action_count(author, target if target != author else None, action)
            count = await get_action_between_users(author.id, target.id, action) if target != author else await get_given_count(author.id, action)
            counter = build_counter_text(action, count, author.display_name, target.display_name if target != author else None)

        reward = await maybe_reward_dabloons(author.id, author.display_name)

        description = base_desc
        if counter:
            description += f"\n{counter}"
        if reward:
            description += f"\n-# ✨ +{reward} dabloons!"

        embed = await build_embed(action_data['color'], title, description, action, author=author)
        await ctx.send(embed=embed)

    @bot.command(name="look")
    async def do_reaction(ctx: commands.Context, reaction: str):
        reaction = reaction.lower()
        if reaction not in REACTIONS:
            return

        await ensure_registered(ctx.author.id, ctx.author.display_name)
        reaction_data = REACTIONS[reaction]
        author = ctx.author

        title = reaction_data['title'].format(author=author)
        base_desc = random.choice(reaction_data['description']).format(author=author)

        await increment_action_count(author, None, reaction)
        count = await get_given_count(author.id, reaction)
        counter = build_counter_text(reaction, count, author.display_name, None, is_look=True)

        reward = await maybe_reward_dabloons(author.id, author.display_name)

        description = base_desc
        if counter:
            description += f"\n{counter}"
        if reward:
            description += f"\n-# ✨ +{reward} dabloons!"

        embed = await build_embed(reaction_data['color'], title, description, reaction, author=author)
        await ctx.send(embed=embed)

    @bot.command(name="rate")
    async def rate(ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        ratings = {
            "smort": random.randint(0, 100), "funny": random.randint(0, 100),
            "rizz": random.randint(0, 100), "hot": random.randint(0, 100),
            "cute": random.randint(0, 100), "gay": random.randint(0, 100),
        }
        mean_rating = statistics.mean(ratings.values())
        embed = discord.Embed(title=f"Rating for {target.display_name}", color=discord.Color.pink())
        embed.set_thumbnail(url=target.display_avatar.url)
        for stat, value in ratings.items():
            embed.add_field(name=stat.capitalize(), value=f"**{value}%**", inline=True)
        embed.set_footer(text=f"overall vibe: {mean_rating:.0f}%")
        await ctx.send(embed=embed)
