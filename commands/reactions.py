import random
import discord
from discord import app_commands
from typing import Optional, Literal
from utils.userbase.ensure_registered import ensure_registered
from utils.action_counts import increment_action_count, maybe_reward_dabloons
from utils.reactions import build_embed, build_title, build_counter_text, ACTIONS, REACTION, React_back

# ── Command setup ─────────────────────────────────────────────────────────────
async def setup_reactions(bot):

    @bot.tree.command(name="do", description="Perform an action with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(
        action="Choose an action to perform",
        user="The person you want to interact with (optional)",
        everyone="Perform the action on everyone (optional)"
    )
    async def do_action(
        interaction: discord.Interaction,
        action: Literal[
            'hug', 'kiss', 'pat', 'poke', 'cuddle', 'bite', 'kick', 'punch',
            'feed', 'highfive', 'dance', 'sleep', 'cry', 'smile', 'think',
            'wave', 'laugh', 'yeet', 'facepalm', 'baka', 'nom', 'shoot',
            'run', 'stare', 'thumbsup'
        ],
        user: Optional[discord.User] = None,
        everyone: Optional[bool] = False
    ):
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            return

        try:
            await ensure_registered(interaction.user.id, str(interaction.user))

            action_data = ACTIONS[action]
            target_name = user.display_name if user else None
            title = build_title(action, action_data, interaction.user.display_name, target_name, everyone)

            # ── Description ───────────────────────────────────────────────────
            if everyone:
                base_desc = random.choice(action_data['desc_everyone']).format(user=interaction.user, author=interaction.user)
            elif user and user == interaction.user:
                base_desc = random.choice(action_data['desc_self']).format(user=interaction.user, author=interaction.user)
            elif user:
                base_desc = random.choice(action_data['desc_other']).format(user=user, author=interaction.user)
            else:
                base_desc = random.choice(action_data['desc_self']).format(user=interaction.user, author=interaction.user)

            # ── Counter (only when targeting another real user) ───────────────
            counter = ''
            if user and user != interaction.user and not everyone and not user.bot:
                count = await increment_action_count(interaction.user.id, user.id, action)
                counter = build_counter_text(action, count, interaction.user.display_name, user.display_name)

            # ── Dabloon reward ────────────────────────────────────────────────
            reward = await maybe_reward_dabloons(interaction.user.id)

            description = base_desc
            if counter:
                description += f'\n{counter}'
            if reward:
                description += f'\n-# ✨ +{reward} dabloons!'

            embed = await build_embed(action_data['color'], title, description, action, author=interaction.user)

            # ── Button — disabled for bot targets ─────────────────────────────
            show_button = not everyone and user != interaction.user and user is not None and not (user is not None and user.bot)
            view = React_back(interaction.user, user, action, show_button=show_button)

            if user is not None and user.bot:
                view.react_back_button.disabled = True

            view.message = await interaction.followup.send(embed=embed, view=view)

            # ── Easter egg: targeting Amber herself ───────────────────────────
            if user == bot.user:
                bot_title = build_title(action, action_data, bot.user.display_name, interaction.user.display_name)
                bot_desc = random.choice(action_data['desc_other']).format(user=interaction.user, author=bot.user)
                bot_embed = await build_embed(action_data['color'], bot_title, bot_desc, action, author=bot.user)
                await interaction.followup.send(embed=bot_embed)

            # ── 50% chance to react back when targeting another bot ────────────
            elif user is not None and user.bot and user != bot.user and random.random() < 0.5:
                bot_title = build_title(action, action_data, user.display_name, interaction.user.display_name)
                bot_desc = random.choice(action_data['desc_other']).format(user=interaction.user, author=user)
                bot_embed = await build_embed(action_data['color'], bot_title, bot_desc, action, author=user)
                await interaction.followup.send(embed=bot_embed)

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="look", description="Give a reaction with a GIF!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.describe(reaction="Choose a reaction to perform")
    async def do_reaction(
        interaction: discord.Interaction,
        reaction: Literal[
            'blush', 'shrug', 'yawn', 'angry', 'bored', 'happy',
            'nope', 'smug', 'lurk', 'pout', 'nod'
        ]
    ):
        await interaction.response.defer()
        try:
            await ensure_registered(interaction.user.id, str(interaction.user))

            reaction_data = REACTION[reaction]
            title = reaction_data['title'].format(author=interaction.user)
            base_desc = random.choice(reaction_data['description']).format(author=interaction.user)

            # Counter: "{user} blushed X times"
            count = await increment_action_count(interaction.user.id, None, reaction)
            counter = build_counter_text(reaction, count, interaction.user.display_name, None, is_look=True)

            # Dabloon reward
            reward = await maybe_reward_dabloons(interaction.user.id)

            description = base_desc
            if counter:
                description += f'\n{counter}'
            if reward:
                description += f'\n-# ✨ +{reward} dabloons!'

            embed = await build_embed(reaction_data['color'], title, description, reaction, author=interaction.user)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="**Error**",
                description=f"Something went wrong!\n```log\n\n{str(e)}\n\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
