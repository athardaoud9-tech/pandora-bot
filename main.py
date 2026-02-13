import discord
from discord.ext import commands
import os
import time
import random
import datetime
import json
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (Anti-Coupure Render) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. GESTION BASE DE DONNÉES (JSON) ---
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- 3. CONFIG DU BOT ---
intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="!", intents=intents)

SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}

@bot.event
async def on_ready():
    print(f"✅ Bot Pandora prêt : {bot.user}")

# --- 4. SYSTÈME DE MORPION (BOUTONS) ---
class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, label: str, row: int, col: int):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row)
        self.row_idx, self.col_idx = row, col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToe = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        if self.label != "⬜": return

        symbol = "❌" if view.current_player == view.p1 else "⭕"
        self.label, self.disabled = symbol, True
        self.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.success
        view.board[self.row_idx][self.col_idx] = symbol
        view.switch_player()

        winner = view.check_winner()
        if winner: await view.end_game(winner)
        elif view.is_full(): await view.end_game(None)
        await interaction.response.edit_message(content=view.get_display(), view=view)

class TicTacToe(discord.ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=300)
        self.p1, self.p2 = p1, p2
        self.current_player = p1
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        for r in range(3):
            for c in range(3): self.add_item(TicTacToeButton("⬜", r, c))

    def get_display(self):
        board_str = "\n".join(["".join(c if c != " " else "⬜" for c in r) for r in self.board])
        return f"🎮 **{self.p1.display_name}** vs **{self.p2.display_name}**\nTour de : **{self.current_player.display_name}**\n```\n{board_str}\n```"

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

    async def end_game(self, win):
        res = f"🏆 **{self.p1.display_name if win == '❌' else self.p2.display_name} a gagné !**" if win else "🤝 Égalité !"
        for c in self.children: c.disabled = True
        self.stop()
        await self.msg.edit(content=self.get_display() + f"\n{res}", view=self)

# --- 5. BIENVENUE & DEPART ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470176904668516528) 
    if channel:
        embed = discord.Embed(description=f"🦋 Bienvenue {member.mention}", color=0x4b41e6)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1470177322161147914)
    if channel:
        await channel.send(f"👋 **{member.display_name}** nous a quittés.")

# --- 6. ECONOMIE (CORRIGÉ) ---
@bot.command()
async def balance(ctx):
    db = load_db()
    await ctx.send(f"💰 {ctx.author.display_name}, tu as **{db.get(str(ctx.author.id), 0)} coins**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 350)
    uid = str(ctx.author.id)
    db[uid] = db.get(uid, 0) + gain
    save_db(db)
    await ctx.send(f"🔨 **{ctx.author.display_name}**, tu as gagné **{gain} coins** !")

@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique Pandora", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items(): em.add_field(name=it.capitalize(), value=f"💰 {pr}", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    item = item.lower().strip()
    if item not in SHOP_ITEMS: return await ctx.send("Article inconnu.")
    if db.get(str(ctx.author.id), 0) < SHOP_ITEMS[item]: return await ctx.send("Pas assez de coins !")
    
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if role:
        db[str(ctx.author.id)] -= SHOP_ITEMS[item]
        save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"🎉 Rôle **{role.name}** acheté !")
    else: await ctx.send("Rôle introuvable sur le serveur.")

@bot.command()
async def morpion(ctx, adv: discord.Member):
    if adv == ctx.author: return
    view = TicTacToe(ctx.author, adv)
    view.msg = await ctx.send(view.get_display(), view=view)

# --- 7. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
