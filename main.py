import discord
from discord.ext import commands
import os
import time
import random
import json
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora est en ligne !"

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

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Articles du Shop (Minuscule obligatoire ici)
SHOP_ITEMS = {
    "vip": 1000, 
    "juif": 10000, 
    "milliardaire": 100000
}

@bot.event
async def on_ready():
    # Synchronise les boutons et commandes
    await bot.tree.sync()
    print(f"✅ Pandora est connecté et prêt !")

# --- 4. CLASSES DES JEUX (INTERFACE BOUTONS) ---

# --- MORPION (TIC TAC TOE) ---
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

        if view.check_winner():
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
        b = self.board
        # Lignes, Colonnes, Diagonales
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != 0: return True
            if b[0][i] == b[1][i] == b[2][i] != 0: return True
        if b[0][0] == b[1][1] == b[2][2] != 0: return True
        if b[0][2] == b[1][1] == b[2][0] != 0: return True
        return False

    def is_full(self): return all(c != 0 for r in self.board for c in r)

# --- BLACKJACK ---
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.amount = amount
        self.db = db
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]
        self.ended = False

    def draw(self): return random.choice(self.deck)

    def score(self, hand):
        s = sum(hand)
        n_aces = hand.count(11)
        while s > 21 and n_aces > 0:
            s -= 10
            n_aces -= 1
        return s

    async def end_game(self, interaction, result_msg):
        self.ended = True
        for child in self.children: child.disabled = True
        
        # Logique de gain/perte
        uid = str(self.author_id)
        if "Gagné" in result_msg:
            self.db[uid] = self.db.get(uid, 0) + (self.amount * 2) # Rembourse + gain
            save_db(self.db)
            color = 0x00ff00
        elif "Égalité" in result_msg:
            self.db[uid] = self.db.get(uid, 0) + self.amount # Rembourse
            save_db(self.db)
            color = 0xffff00
        else:
            # Déjà perdu au lancement
            color = 0xff0000
            
        embed = discord.Embed(title="🃏 Blackjack", description=result_msg, color=color)
        embed.add_field(name="Vos cartes", value=f"{self.player_hand} (Total: {self.score(self.player_hand)})")
        embed.add_field(name="Croupier", value=f"{self.dealer_hand} (Total: {self.score(self.dealer_hand)})")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        if self.score(self.player_hand) > 21:
            await self.end_game(interaction, "💥 Tu as sauté (Bust) ! Perdu.")
        else:
            embed = discord.Embed(title="🃏 Blackjack - Ton tour", color=0x4b41e6)
            embed.add_field(name="Vos cartes", value=f"{self.player_hand} (Total: {self.score(self.player_hand)})")
            embed.add_field(name="Croupier", value=f"[{self.dealer_hand[0]}, ?]")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        # Tour du croupier
        while self.score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw())
        
        ps = self.score(self.player_hand)
        ds = self.score(self.dealer_hand)
        
        if ds > 21: await self.end_game(interaction, "🎉 Le croupier a sauté ! Tu as Gagné !")
        elif ps > ds: await self.end_game(interaction, "🎉 Tu as Gagné !")
        elif ps == ds: await self.end_game(interaction, "🤝 Égalité !")
        else: await self.end_game(interaction, "❌ Le croupier gagne. Perdu.")

# --- 5. COMMANDES DE JEUX ---

@bot.command()
async def morpion(ctx, member: discord.Member):
    if member.bot or member == ctx.author: return await ctx.send("Adversaire invalide.")
    await ctx.send(f"🎮 **Morpion** : {ctx.author.mention} vs {member.mention}", view=TicTacToeView(ctx.author, member))

@bot.command()
async def blackjack(ctx, amount: int):
    db = load_db()
    uid = str(ctx.author.id)
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    # On retire la mise immédiatement
    db[uid] -= amount
    save_db(db)
    
    view = BlackjackView(ctx.author.id, amount, db)
    embed = discord.Embed(title="🃏 Blackjack", description=f"Mise : **{amount} coins**", color=0x4b41e6)
    embed.add_field(name="Vos cartes", value=f"{view.player_hand} (Total: {view.score(view.player_hand)})")
    embed.add_field(name="Croupier", value=f"[{view.dealer_hand[0]}, ?]")
    await ctx.send(embed=embed, view=view)

@bot.command()
async def roulette(ctx, amount: int, choice: str):
    choice = choice.lower()
    if choice not in ["noir", "rouge"]:
        return await ctx.send("❌ Choisis **rouge** ou **noir** (ex: `!roulette 100 rouge`).")
    
    db = load_db()
    uid = str(ctx.author.id)
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    colors = ["rouge", "noir"]
    result = random.choice(colors)
    
    if choice == result:
        gain = amount # On gagne sa mise (donc on récupère mise + gain)
        db[uid] += gain
        save_db(db)
        await ctx.send(f"🎰 La boule tombe sur **{result.upper()}** ! Tu gagnes **{amount} coins** !")
    else:
        db[uid] -= amount
        save_db(db)
        await ctx.send(f"🎰 La boule tombe sur **{result.upper()}**. Tu as perdu ta mise.")

# --- 6. ÉCONOMIE CLASSIQUE (WORK, DAILY, ROB, GIVE) ---

@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author: 
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("Impossible.")
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    
    if v_bal < 200:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❌ La cible est trop pauvre (min 200 coins).")
    
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(f"🥷 Tu as volé **{stolen} coins** à **{member.display_name}** !")
    else:
        fine = 100
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(f"👮 **Arrêté !** Tu payes une amende de **{fine} coins**.")

@bot.command(name="give")
async def give_money(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("❌ Montant invalide.")
    db = load_db()
    uid = str(ctx.author.id)
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    db[uid] -= amount
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db)
    await ctx.send(f"💸 Virement de **{amount} coins** envoyé à **{member.display_name}**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 350)
    uid = str(ctx.author.id)
    db[uid] = db.get(uid, 0) + gain
    save_db(db)
    await ctx.send(f"🔨 Tu as travaillé et gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_last_daily"
    if time.time() - db.get(key, 0) < 43200:
        return await ctx.send("⏳ Reviens plus tard (Cooldown 12h).")
    gain = random.randint(500, 1000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(f"🎁 Daily réclamé : **+{gain} coins** !")

@bot.command()
async def bal(ctx):
    db = load_db()
    await ctx.send(f"💰 Solde : **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 7. ADMIN & SHOP ---

@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    db = load_db()
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db)
    await ctx.send(f"👑 Admin Give : +{amount} pour {member.display_name}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    db[uid] = max(0, db.get(uid, 0) - amount)
    save_db(db)
    await ctx.send(f"📉 Taxe : -{amount} pour {member.display_name}.")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for k, v in SHOP_ITEMS.items():
        embed.add_field(name=k.upper(), value=f"💰 {v} coins", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item_clean = item.lower().strip()
    
    if item_clean not in SHOP_ITEMS:
        return await ctx.send("❌ Cet article n'existe pas.")
    
    price = SHOP_ITEMS[item_clean]
    
    # Recherche robuste du rôle (insensible à la casse)
    role = discord.utils.find(lambda r: r.name.lower() == item_clean, ctx.guild.roles)
    
    if not role:
        return await ctx.send(f"⚠️ Erreur config : Le rôle **{item_clean}** n'existe pas sur le serveur Discord !")
    
    if role in ctx.author.roles:
        return await ctx.send("❌ Tu as déjà ce rôle.")
    
    if db.get(uid, 0) < price:
        return await ctx.send(f"❌ Pas assez d'argent (Manque {price - db.get(uid, 0)}).")
    
    try:
        db[uid] -= price
        save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"🎉 Tu as acheté le grade **{role.name}** !")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de donner ce rôle (vérifie la hiérarchie).")

@bot.command()
async def help(ctx):
    em = discord.Embed(title="Aide Pandora", color=0x4b41e6)
    em.add_field(name="💰 Gains", value="`!work`, `!daily`, `!rob @user`", inline=True)
    em.add_field(name="🎲 Jeux", value="`!roulette <mise> <couleur>`, `!blackjack <mise>`, `!morpion @user`", inline=True)
    em.add_field(name="💳 Banque", value="`!bal`, `!give @user <montant>`, `!shop`, `!buy <item>`", inline=False)
    await ctx.send(embed=em)

# --- 8. ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown ! Attends {int(error.retry_after)}s.", delete_after=5)

# --- 9. LANCEMENT ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
