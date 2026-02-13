import discord
from discord.ext import commands
import os
import time
import random
import json
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (Render) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES ---
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
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- CONFIGURATION DU SHOP ---
SHOP_ITEMS = {
    "vip": 1000, 
    "juif": 10000, 
    "milliardaire": 100000
}

@bot.event
async def on_ready():
    # Nettoyage des commandes slash au démarrage
    await bot.tree.set_global_commands(commands=None)
    await bot.tree.sync()
    print(f"✅ Pandora est Live | Commandes slash nettoyées")

# --- 4. SYSTÈME DE MORPION ---
class TicTacToeButton(discord.ui.Button["TicTacToeView"]):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y)
        self.x, self.y = x, y

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        if self.label != "⬜": return

        if view.current_player == view.p1:
            self.label, self.style, view.board[self.y][self.x] = "❌", discord.ButtonStyle.danger, 1
            view.current_player = view.p2
        else:
            self.label, self.style, view.board[self.y][self.x] = "⭕", discord.ButtonStyle.success, 2
            view.current_player = view.p1

        winner = view.check_winner()
        if winner:
            for child in view.children: child.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{interaction.user.display_name} a gagné !**", view=view)
        elif view.is_full():
            await interaction.response.edit_message(content="🤝 **Match nul !**", view=view)
        else:
            await interaction.response.edit_message(content=f"Tour de : **{view.current_player.display_name}**", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2):
        super().__init__()
        self.p1, self.p2, self.current_player = p1, p2, p1
        self.board = [[0, 0, 0] for _ in range(3)]
        for y in range(3):
            for x in range(3): self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0: return True
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0: return True
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0: return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0: return True
        return False

    def is_full(self): return all(c != 0 for r in self.board for c in r)

# --- 5. COMMANDES ÉCONOMIE & VOL ---
@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return await ctx.send("❓ Tu ne peux pas te voler toi-même.")
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    if v_bal < 200: 
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❌ La cible est trop pauvre (min 200).")
    
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(f"🥷 **Succès !** Tu as dérobé **{stolen} coins** à {member.display_name} !")
    else:
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - 100)
        save_db(db)
        await ctx.send("👮 **Échec !** Tu as été arrêté et tu payes une amende de **100 coins**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 350)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(f"🔨 **{ctx.author.display_name}**, tu as gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_last_daily"
    if time.time() - db.get(key, 0) < 43200:
        reste = int(43200 - (time.time() - db.get(key, 0)))
        return await ctx.send(f"⏳ Reviens dans **{reste // 3600}h {(reste % 3600) // 60}min**.")
    gain = random.randint(500, 1000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(f"🎁 **Bonus Daily :** +**{gain} coins** !")

@bot.command()
async def bal(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, tu as **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 6. COMMANDE SHOP & BUY ---
@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique Pandora", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items():
        em.add_field(name=it.capitalize(), value=f"💰 {pr} coins", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item = item.lower().strip()
    
    if item not in SHOP_ITEMS:
        return await ctx.send("❌ Cet article n'existe pas.")
    
    prix = SHOP_ITEMS[item]
    if db.get(uid, 0) < prix:
        return await ctx.send("❌ Tu n'as pas assez d'argent !")
    
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if role:
        try:
            db[uid] -= prix
            save_db(db)
            await ctx.author.add_roles(role)
            await ctx.send(f"🎉 Félicitations ! Tu as acheté le rôle **{role.name}** !")
        except:
            await ctx.send("❌ Erreur : Vérifie que mon rôle est bien au-dessus des autres !")
    else:
        await ctx.send(f"⚠️ Le rôle **{item}** doit être créé sur le serveur.")

# --- 7. ADMIN (GIVE, TAX, HELP) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    db = load_db(); db[str(member.id)] = db.get(str(member.id), 0) + amount; save_db(db)
    await ctx.send(f"✅ **{amount} coins** ajoutés à {member.display_name}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    db[uid] = max(0, db.get(uid, 0) - amount); save_db(db)
    await ctx.send(f"💸 **{member.display_name}** a été taxé de **{amount} coins**.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 Aide Pandora", color=0x4b41e6)
    embed.add_field(name="💰 Éco", value="`!work`, `!daily`, `!bal`, `!rob @user`, `!shop`, `!buy`", inline=False)
    embed.add_field(name="🎮 Fun", value="`!morpion @user`")
    embed.add_field(name="🛡️ Admin", value="`!give`, `!tax`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def morpion(ctx, member: discord.Member):
    if member.bot or member == ctx.author: return
    await ctx.send(f"🎮 Tour : {ctx.author.name}", view=TicTacToeView(ctx.author, member))

# --- 8. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
