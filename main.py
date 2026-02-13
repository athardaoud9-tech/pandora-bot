import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from flask import Flask
from threading import Thread

# --- SYSTÈME ANTI-COUPURE RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Bot est en ligne !"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION DU BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    try:
        with open("database.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("database.json", "w") as f: json.dump(data, f, indent=4)

# --- CLASSES DU JEU DE MORPION (TIC-TAC-TOE) ---
class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, label: str, row: int, col: int):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row)
        self.row_idx, self.col_idx = row, col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToe = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        if self.label not in ("⬜"):
            return await interaction.response.send_message("Case déjà jouée !", ephemeral=True)

        symbol = "❌" if view.current_player == view.p1 else "⭕"
        self.label, self.disabled = symbol, True
        self.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.success
        view.board[self.row_idx][self.col_idx] = symbol
        view.switch_player()

        winner = view.check_winner()
        if winner: await view.end_game(winner_symbol=winner)
        elif view.is_full(): await view.end_game(winner_symbol=None)
        await interaction.response.edit_message(content=view.get_display(), view=view)

class TicTacToe(discord.ui.View):
    def __init__(self, p1, p2, best_of):
        super().__init__(timeout=900)
        self.p1, self.p2, self.best_of = p1, p2, best_of
        self.score, self.round = {p1: 0, p2: 0}, 1
        self.current_player = random.choice([p1, p2])
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.msg = None
        for r in range(3):
            for c in range(3): self.add_item(TicTacToeButton("⬜", r, c))

    def get_display(self):
        board_str = "\n".join(["".join("⬜" if c == " " else c for c in r) for r in self.board])
        return f"**Manche {self.round}/{self.best_of}** | {self.p1.name} {self.score[self.p1]}–{self.score[self.p2]} {self.p2.name}\n→ **{self.current_player.name}**\n```\n{board_str}\n```"

    def switch_player(self): self.current_player = self.p2 if self.current_player == self.p1 else self.p1
    def is_full(self): return all(c != " " for r in self.board for c in r)
    def check_winner(self):
        for r in self.board: 
            if r[0] == r[1] == r[2] != " ": return r[0]
        for c in range(3):
            if self.board[0][c] == self.board[1][c] == self.board[2][c] != " ": return self.board[0][c]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != " ": return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != " ": return self.board[0][2]
        return None

    async def end_game(self, winner_symbol):
        if winner_symbol:
            w = self.p1 if winner_symbol == "❌" else self.p2
            self.score[w] += 1
            res = f"**{w.name} gagne la manche !**"
        else: res = "**Égalité !**"

        if self.score[self.p1] > self.best_of//2 or self.score[self.p2] > self.best_of//2:
            win_final = self.p1 if self.score[self.p1] > self.best_of//2 else self.p2
            res += f"\n🏆 **{win_final.name} remporte la partie !**"
            for c in self.children: c.disabled = True
            self.stop()
        else:
            self.round += 1
            self.board = [[" " for _ in range(3)] for _ in range(3)]
            for c in self.children: c.label, c.style, c.disabled = "⬜", discord.ButtonStyle.secondary, False
        await self.msg.edit(content=self.get_display() + f"\n{res}", view=self)

class InviteMorpion(discord.ui.View):
    def __init__(self, challenger, opponent, manches):
        super().__init__(timeout=60)
        self.challenger, self.opponent, self.manches = challenger, opponent, manches

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button):
        if interaction.user != self.opponent: return
        game = TicTacToe(self.challenger, self.opponent, self.manches)
        await interaction.message.delete()
        game.msg = await interaction.channel.send(game.get_display(), view=game)

# --- COMMANDES CLASSIQUES (!) ---

@bot.command()
async def morpion(ctx, adversaire: discord.Member, manches: int = 3):
    if adversaire == ctx.author: return await ctx.send("Joue pas tout seul !")
    view = InviteMorpion(ctx.author, adversaire, manches)
    await ctx.send(f"🎮 {adversaire.mention}, défi de {ctx.author.mention} au Morpion !", view=view)

@bot.command()
async def work(ctx):
    data = load_data()
    gain = random.randint(100, 400)
    data[str(ctx.author.id)] = {"balance": data.get(str(ctx.author.id), {}).get("balance", 0) + gain}
    save_data(data)
    await ctx.send(f"🛠️ Tu as gagné **{gain}$** !")

@bot.command()
async def rob(ctx, member: discord.Member):
    data = load_data()
    if data.get(str(member.id), {}).get("balance", 0) < 200: return await ctx.send("Trop pauvre !")
    vol = random.randint(50, 150)
    data[str(ctx.author.id)]["balance"] = data.get(str(ctx.author.id), {}).get("balance", 0) + vol
    data[str(member.id)]["balance"] -= vol
    save_data(data)
    await ctx.send(f"🥷 Tu as volé **{vol}$** à {member.mention} !")

@bot.command()
async def money(ctx, member: discord.Member = None):
    m = member or ctx.author
    bal = load_data().get(str(m.id), {}).get("balance", 0)
    await ctx.send(f"🪙 {m.name} a **{bal}$**.")

@bot.event
async def on_ready(): print(f"✅ {bot.user} en ligne sur Render !")

keep_alive()
bot.run(os.getenv('TOKEN'))
