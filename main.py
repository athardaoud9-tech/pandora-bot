import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio
from flask import Flask
from threading import Thread

# --- SERVEUR POUR RENDER (Anti-Timeout) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION DU BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- GESTION DE LA BASE DE DONNÉES ---
def load_data():
    try:
        with open("database.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("database.json", "w") as f: json.dump(data, f, indent=4)

# --- CLASSES DU JEU DE MORPION ---
class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, label: str, row: int, col: int):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row)
        self.row_idx = row
        self.col_idx = col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToe = self.view
        if interaction.user != view.current_player:
            await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
            return
        if self.label not in ("⬜", "❌", "⭕"):
            await interaction.response.send_message("Cette case est déjà jouée !", ephemeral=True)
            return

        symbol = "❌" if view.current_player == view.p1 else "⭕"
        self.label = symbol
        self.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.success
        self.disabled = True
        view.board[self.row_idx][self.col_idx] = symbol
        view.switch_player()

        winner = view.check_winner()
        if winner: await view.end_game(winner_symbol=winner)
        elif view.is_full(): await view.end_game(winner_symbol=None)
        await interaction.response.edit_message(content=view.get_display(), view=view)

class TicTacToe(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member, best_of: int):
        super().__init__(timeout=900)
        self.p1, self.p2, self.best_of = p1, p2, best_of
        self.score = {p1: 0, p2: 0}
        self.round = 1
        self.current_player = random.choice([p1, p2])
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.msg = None
        for r in range(3):
            for c in range(3): self.add_item(TicTacToeButton("⬜", r, c))

    def get_display(self):
        board_str = "\n".join(["".join("⬜" if c == " " else c for c in r) for r in self.board])
        return f"**Manche {self.round}/{self.best_of}** | {self.p1.display_name} {self.score[self.p1]} – {self.score[self.p2]} {self.p2.display_name}\n→ **{self.current_player.display_name}** ({'❌' if self.current_player == self.p1 else '⭕'})\n\n```\n{board_str}\n```"

    def switch_player(self): self.current_player = self.p2 if self.current_player == self.p1 else self.p1

    def check_winner(self):
        for r in self.board: 
            if r[0] == r[1] == r[2] != " ": return r[0]
        for c in range(3):
            if self.board[0][c] == self.board[1][c] == self.board[2][c] != " ": return self.board[0][c]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != " ": return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != " ": return self.board[0][2]
        return None

    def is_full(self): return all(c != " " for r in self.board for c in r)

    async def end_game(self, winner_symbol: str | None):
        if winner_symbol:
            winner = self.p1 if winner_symbol == "❌" else self.p2
            self.score[winner] += 1
            msg = f"**{winner.display_name} gagne la manche !**"
        else: msg = "**Égalité !**"

        to_win = (self.best_of // 2) + 1
        if self.score[self.p1] >= to_win or self.score[self.p2] >= to_win:
            winner_final = self.p1 if self.score[self.p1] >= to_win else self.p2
            msg += f"\n\n🏆 **{winner_final.display_name} remporte la série !**"
            for c in self.children: c.disabled = True
            self.stop()
        else:
            self.round += 1
            self.board = [[" " for _ in range(3)] for _ in range(3)]
            for c in self.children:
                c.label, c.style, c.disabled = "⬜", discord.ButtonStyle.secondary, False
            msg += "\nNouvelle manche..."
        await self.msg.edit(content=self.get_display() + f"\n{msg}", view=self)

class InviteView(discord.ui.View):
    def __init__(self, challenger, opponent, best_of):
        super().__init__(timeout=180)
        self.challenger, self.opponent, self.best_of = challenger, opponent, best_of

    @discord.ui.button(label="Accepter ✓", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button):
        if interaction.user != self.opponent: return
        await interaction.message.edit(content="Partie acceptée !", view=None)
        game = TicTacToe(self.challenger, self.opponent, self.best_of)
        game.msg = await interaction.channel.send(game.get_display(), view=game)
        self.stop()

    @discord.ui.button(label="Refuser ✗", style=discord.ButtonStyle.red)
    async def refuse(self, interaction: discord.Interaction, button):
        if interaction.user != self.opponent: return
        await interaction.message.edit(content="Partie refusée.", view=None)
        self.stop()

# --- COMMANDES SLASH ---

@bot.tree.command(name="morpion", description="Défier quelqu'un au morpion")
async def start_morpion(interaction: discord.Interaction, adversaire: discord.Member, manches: int = 3):
    if adversaire == interaction.user: return await interaction.response.send_message("Pas contre toi-même !", ephemeral=True)
    if manches % 2 == 0: return await interaction.response.send_message("Nombre de manches impair requis.", ephemeral=True)
    view = InviteView(interaction.user, adversaire, manches)
    await interaction.response.send_message(f"{adversaire.mention}, défi de {interaction.user.mention} !", view=view)

@bot.tree.command(name="daily", description="Argent quotidien (12h)")
@app_commands.checks.cooldown(1, 43200)
async def daily(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    data[uid] = data.get(uid, {"balance": 0})
    data[uid]["balance"] += 500
    save_data(data)
    await interaction.response.send_message("💰 +500$ ! (Reviens dans 12h)")

@bot.tree.command(name="roulette", description="Mise sur rouge/noir")
async def roulette(interaction: discord.Interaction, mise: int, couleur: str):
    data = load_data()
    uid = str(interaction.user.id)
    if data.get(uid, {}).get("balance", 0) < mise: return await interaction.response.send_message("Pas assez d'argent.")
    res = random.choice(["rouge", "noir"])
    if couleur.lower() == res:
        data[uid]["balance"] += mise
        await interaction.response.send_message(f"🎰 GAGNÉ ! C'était {res}.")
    else:
        data[uid]["balance"] -= mise
        await interaction.response.send_message(f"🎰 PERDU... C'était {res}.")
    save_data(data)

@bot.tree.command(name="shop", description="Voir la boutique")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Shop", description="**Rôle VIP** : 50,000$\n**Badge** : 10,000$")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taxe", description="Taxer un membre (Admin)")
@app_commands.checks.has_permissions(administrator=True)
async def taxe(interaction: discord.Interaction, membre: discord.Member, montant: int):
    data = load_data()
    uid = str(membre.id)
    if uid in data:
        data[uid]["balance"] -= montant
        save_data(data)
        await interaction.response.send_message(f"💸 {montant}$ retirés à {membre.mention}.")

# --- LANCEMENT ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté et synchronisé !")

keep_alive() # Pour Render
bot.run(os.getenv('TOKEN'))
