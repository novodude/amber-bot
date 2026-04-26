from asyncio import sleep
import discord
import random
import requests
import aiosqlite
from typing import Literal
import discord.ui as ui
from utils.economy import add_dabloons, add_xp, get_dabloons
from utils.userbase.ensure_registered import ensure_registered
from utils.quests import increment_quest_progress
from discord import app_commands


class DuckClicker(ui.View):
    def __init__(self, user_id: int, discord_id: int):
        super().__init__(timeout=None)
        self.click_count = 0        # total all-time score
        self.session_clicks = 0     # clicks this session (for quest tracking)
        self.user_id = user_id
        self.discord_id = discord_id

    async def load_score(self):
        async with aiosqlite.connect("data/user.db") as db:
            cursor = await db.execute(
                "SELECT duck_clicker_current_score FROM games WHERE user_id = ?", (self.user_id,)
            )
            row = await cursor.fetchone()
            self.click_count = row[0] if row and row[0] is not None else 0

    async def save_score(self):
        async with aiosqlite.connect("data/user.db") as db:
            await db.execute(
                "UPDATE games SET duck_clicker_current_score = ? WHERE user_id = ?",
                (self.click_count, self.user_id)
            )
            await db.commit()

    @discord.ui.button(label="🦆 quack!", style=discord.ButtonStyle.primary, row=0)
    async def click_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This isn't your duck clicker!", ephemeral=True)
            return

        self.click_count += 1
        self.session_clicks += 1
        await self.save_score()

        # ── quest progress ────────────────────────────────────────────────────
        await increment_quest_progress(self.discord_id, "duck_clicks", amount=1)

        message = f"**{self.click_count}** ducks quacked! 🦆"

        if self.click_count % 5 == 0:
            await add_dabloons(self.user_id, 2)
            message += "\n✨ **+2 dabloons!** keep on clicking :D"

        await interaction.response.edit_message(content=message, view=self)


class TicTacToe(ui.View):
    def __init__(self, user_id: int, discord_id: int, difficulty: str, difficulty_level: float):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.discord_id = discord_id
        self.difficulty = difficulty
        self.difficulty_level = difficulty_level
        self.board = [None] * 9
        self.player_symbol = "❌"
        self.ai_symbol = "⭕️"
        self.current_player = "❌"
        self.ai_enabled = True
        self.game_over = False

        for i in range(9):
            button = ui.Button(
                label="*",
                style=discord.ButtonStyle.secondary,
                row=i // 3,
                custom_id=f"cell_{i}"
            )
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, position):
        async def callback(interaction: discord.Interaction):
            if (not interaction.user or self.board[position] is not None
                    or self.game_over or self.current_player != self.player_symbol):
                return

            await interaction.response.defer()
            await self.make_move(interaction, position)

            if self.ai_enabled and not self.game_over and self.current_player == self.ai_symbol:
                ai_move = self.get_best_move()
                if ai_move is not None:
                    await self.make_move(interaction, ai_move, is_ai=True)

        return callback

    async def make_move(self, interaction, position, is_ai=False):
        self.board[position] = self.current_player

        button = self.children[position]
        button.label = self.current_player
        button.style = (
            discord.ButtonStyle.danger
            if self.current_player == self.player_symbol
            else discord.ButtonStyle.success
        )
        button.disabled = True

        winner = self.check_winner()
        if winner:
            self.game_over = True
            self.disable_all_buttons()

            if winner == self.player_symbol:
                rewards = {"easy": 4, "medium": 8, "hard": 16}
                reward = rewards[self.difficulty]
                await add_dabloons(self.user_id, reward)
                await add_xp(self.user_id, reward * 10, None)

                # ── quest progress ────────────────────────────────────────────
                await increment_quest_progress(self.discord_id, "ttt_win", amount=1)

                content = f"You win! 🎉 +{reward} dabloons"
            elif winner == "Tie":
                content = "It's a tie!"
            else:
                content = "AI wins 😈"

            await interaction.edit_original_response(content=content, view=self)
            return

        self.current_player = (
            self.ai_symbol if self.current_player == self.player_symbol
            else self.player_symbol
        )
        await interaction.edit_original_response(view=self)

    def get_best_move(self):
        if random.random() > self.difficulty_level:
            available_moves = [i for i in range(9) if self.board[i] is None]
            return random.choice(available_moves) if available_moves else None

        best_score = -float('inf')
        best_move = None

        for i in range(9):
            if self.board[i] is None:
                self.board[i] = self.ai_symbol
                score = self.minimax(0, False)
                self.board[i] = None
                if score > best_score:
                    best_score = score
                    best_move = i

        return best_move

    def minimax(self, depth, is_maximizing):
        winner = self.check_winner()
        if winner == self.ai_symbol:
            return 10 - depth
        elif winner == self.player_symbol:
            return depth - 10
        elif winner == "Tie":
            return 0

        if is_maximizing:
            best_score = -float('inf')
            for i in range(9):
                if self.board[i] is None:
                    self.board[i] = self.ai_symbol
                    score = self.minimax(depth + 1, False)
                    self.board[i] = None
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for i in range(9):
                if self.board[i] is None:
                    self.board[i] = self.player_symbol
                    score = self.minimax(depth + 1, True)
                    self.board[i] = None
                    best_score = min(score, best_score)
            return best_score

    def check_winner(self):
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for combo in winning_combinations:
            if (self.board[combo[0]] is not None and
                    self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]]):
                return self.board[combo[0]]
        if all(cell is not None for cell in self.board):
            return "Tie"
        return None

    def disable_all_buttons(self):
        for button in self.children:
            button.disabled = True




class Games(app_commands.Group):
    def __init__(self):
        super().__init__(name="games", description="games commands")

    @app_commands.command(name="duck_clicker", description="Click the buttons to quack ducks!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def duck_clicker(self, interaction: discord.Interaction):
        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        view = DuckClicker(user_id, interaction.user.id)
        await view.load_score()
        await interaction.response.send_message(
            f"**{view.click_count}** ducks quacked! 🦆",
            view=view
        )

    @app_commands.command(name="tic_tac_toe", description="Play a game of tic tac toe!")
    @app_commands.describe(difficulty="Choose AI difficulty")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def ttt_command(
        self,
        interaction: discord.Interaction,
        difficulty: Literal["easy", "medium", "hard"]
    ):
        await interaction.response.defer()

        user_id = await ensure_registered(interaction.user.id, str(interaction.user))

        balance = await get_dabloons(user_id)
        cost_map = {"easy": 2, "medium": 4, "hard": 8}
        cost = cost_map[difficulty]

        if balance < cost:
            await interaction.followup.send(
                f"You need at least **{cost} dabloons** to play on {difficulty} difficulty!",
                ephemeral=True
            )
            return

        await add_dabloons(user_id, -cost)

        difficulty_mapping = {"easy": 0.7, "medium": 0.75, "hard": 0.9}
        difficulty_value = difficulty_mapping[difficulty]
        view = TicTacToe(
            user_id=user_id,
            discord_id=interaction.user.id,
            difficulty=difficulty,
            difficulty_level=difficulty_value
        )
        await interaction.followup.send("Tic Tac Toe! You are ❌'s!", view=view)

    @app_commands.command(name="trivia", description="Answer trivia questions and win dabloons!")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def trivia(self, interaction: discord.Interaction):
        res = requests.get("https://opentdb.com/api.php?amount=1")
        data = res.json()

        question = data["results"][0]
        category = question["category"]
        difficulty = question["difficulty"]
        question_text = question["question"]
        correct_answer = question["correct_answer"]

        options = question["incorrect_answers"] + [correct_answer]
        random.shuffle(options)

        embed = discord.Embed(
            title=f"Trivia - {category} ({difficulty})",
            description=f"{question_text}?",
            color=discord.Color.blue()
        )
        for idx, option in enumerate(options):
            embed.add_field(name=f"Option {idx + 1}", value=option, inline=False)
        embed.set_footer(text="You have 20 seconds before the correct answer is revealed!")

        await interaction.response.send_message(embed=embed)
        await sleep(20)
        correct_answer = discord.Embed(
            title=f"{question_text}?",
            description=f"⏰ Time's up! The correct answer was: **{correct_answer}**",
            color=discord.Color.blue()
        )
        await interaction.edit_original_response(embed=correct_answer)





async def minigames_setup(bot):
    games = Games()
    bot.tree.add_command(games)
