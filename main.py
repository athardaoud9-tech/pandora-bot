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

# --- 3. CONFIGURATION DU BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ID DU SALON DE BIENVENUE (Remplace par le tien si ça a changé)
WELCOME_CHANNEL_ID = 1470176904668516528 

SHOP_ITEMS = {
    "vip": 1000, 
    "juif": 10000, 
    "milliardaire": 100000
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora est connecté et prêt !")

# --- 4. SYSTEME BIENVENUE & AU REVOIR ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        # Chemin vers ton GIF de bienvenue
        file_path = "static/images/background.gif"
        if os.path.exists(file_path):
            file = discord.File(file_path, filename="welcome.gif")
            embed = discord.Embed(description=f"🦋 **Bienvenue** {member.mention} sur le serveur !", color=0x4b41e6)
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(embed=embed, file=file)
        else:
            await channel.send(f"Bienvenue {member.mention} ! (GIF introuvable)")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        # Chemin vers ton GIF de départ
        file_path = "static/images/leave.gif"
        if os.path.exists(file_path):
            file = discord.File(file_path, filename="leave.gif")
            embed = discord.Embed(description=f"😢 **Au revoir** {member.display_name}...", color=0xff0000)
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)

# --- 5. CLASSES JEUX (MORPION & BLACKJACK) ---
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
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != 0: return True
            if b[0][i] == b[1][i] == b[2][i] != 0: return True
        if b[0][0] == b[1][1] == b[2][2] != 0: return True
        if b[0][2] == b[1][1] == b[2][0] != 0: return True
        return False
    def is_full(self): return all(c != 0 for r in self.board for c in r)

class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=60)
        self.author_id, self.amount, self.db = author_id, amount, db
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]

    def draw(self): return random.choice(self.deck)
    def score(self, hand):
        s = sum(hand); n_aces = hand.count(11)
        while s > 21 and n_aces > 0: s -= 10; n_aces -= 1
        return s

    async def end_game(self, interaction, result_msg, win_mult):
        for child in self.children: child.disabled = True
        uid = str(self.author_id)
        if win_mult > 0:
            self.db[uid] = self.db.get(uid, 0) + int(self.amount * win_mult)
            save_db(self.db)
            color = 0x00ff00
        else: color = 0xff0000
        
        embed = discord.Embed(title="🃏 Blackjack", description=result_msg, color=color)
        embed.add_field(name="Toi", value=f"{self.player_hand} ({self.score(self.player_hand)})")
        embed.add_field(name="Croupier", value=f"{self.dealer_hand} ({self.score(self.dealer_hand)})")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        if self.score(self.player_hand) > 21: await self.end_game(interaction, "💥 Tu as sauté ! Perdu.", 0)
        else:
            embed = discord.Embed(title="🃏 Blackjack", color=0x4b41e6)
            embed.add_field(name="Toi", value=f"{self.player_hand} ({self.score(self.player_hand)})")
            embed.add_field(name="Croupier", value=f"[{self.dealer_hand[0]}, ?]")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        while self.score(self.dealer_hand) < 17: self.dealer_hand.append(self.draw())
        ps, ds = self.score(self.player_hand), self.score(self.dealer_hand)
        if ds > 21: await self.end_game(interaction, "🎉 Le croupier a sauté ! Tu gagnes !", 2)
        elif ps > ds: await self.end_game(interaction, "🎉 Tu gagnes !", 2)
        elif ps == ds: await self.end_game(interaction, "🤝 Égalité (Remboursé).", 1)
        else: await self.end_game(interaction, "❌ Le croupier gagne.", 0)

# --- 6. COMMANDES JEUX ---
@bot.command()
async def morpion(ctx, member: discord.Member):
    if member.bot or member == ctx.author: return await ctx.send("Adversaire invalide.")
    await ctx.send(f"🎮 {ctx.author.mention} vs {member.mention}", view=TicTacToeView(ctx.author, member))

@bot.command()
async def blackjack(ctx, amount: int):
    db = load_db(); uid = str(ctx.author.id)
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    db[uid] -= amount; save_db(db)
    view = BlackjackView(ctx.author.id, amount, db)
    embed = discord.Embed(title="🃏 Blackjack", description=f"Mise: {amount}", color=0x4b41e6)
    embed.add_field(name="Toi", value=f"{view.player_hand} ({view.score(view.player_hand)})")
    embed.add_field(name="Croupier", value=f"[{view.dealer_hand[0]}, ?]")
    await ctx.send(embed=embed, view=view)

@bot.command()
async def roulette(ctx, amount: int, choice: str):
    choice = choice.lower()
    if choice not in ["noir", "rouge"]: return await ctx.send("❌ `!roulette <mise> rouge/noir`")
    db = load_db(); uid = str(ctx.author.id)
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    colors = ["rouge", "noir"]; result = random.choice(colors)
    if choice == result:
        db[uid] += amount; save_db(db) # Gagne sa mise (donc +mise au total)
        await ctx.send(f"🎰 **{result.upper()}** ! Tu gagnes **{amount} coins** !")
    else:
        db[uid] -= amount; save_db(db)
        await ctx.send(f"🎰 **{result.upper()}** ! Tu perds ta mise.")

# --- 7. COMMANDES ÉCONOMIE ---
@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return
    db = load_db(); v_bal = db.get(str(member.id), 0)
    if v_bal < 200: ctx.command.reset_cooldown(ctx); return await ctx.send("❌ Trop pauvre.")
    
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] += stolen; db[str(member.id)] -= stolen; save_db(db)
        await ctx.send(f"🥷 Vol réussi : **{stolen} coins** !")
    else:
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - 100); save_db(db)
        await ctx.send("👮 Raté ! Amende de **100 coins**.")

@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0: return
    db = load_db(); uid = str(ctx.author.id)
    if db.get(uid, 0) < amount: return await ctx.send("❌ Fonds insuffisants.")
    db[uid] -= amount; db[str(member.id)] = db.get(str(member.id), 0) + amount; save_db(db)
    await ctx.send(f"💸 **{amount} coins** envoyés à {member.display_name}.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db(); gain = random.randint(100, 350)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain; save_db(db)
    await ctx.send(f"🔨 Tu as gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_last_daily"
    if time.time() - db.get(key, 0) < 43200: return await ctx.send("⏳ Reviens plus tard.")
    gain = random.randint(500, 1000)
    db[uid] = db.get(uid, 0) + gain; db[key] = time.time(); save_db(db)
    await ctx.send(f"🎁 Daily : **+{gain} coins** !")

@bot.command()
async def bal(ctx):
    db = load_db(); await ctx.send(f"💰 Solde : **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 8. ADMIN & SHOP ---
@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    db = load_db(); db[str(member.id)] = db.get(str(member.id), 0) + amount; save_db(db)
    await ctx.send(f"👑 Admin Give : +{amount} pour {member.display_name}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id); db[uid] = max(0, db.get(uid, 0) - amount); save_db(db)
    await ctx.send(f"📉 Taxe : -{amount} pour {member.display_name}.")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for k, v in SHOP_ITEMS.items(): embed.add_field(name=k.upper(), value=f"💰 {v}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db(); uid = str(ctx.author.id); item_clean = item.lower().strip()
    if item_clean not in SHOP_ITEMS: return await ctx.send("❌ Article inconnu.")
    price = SHOP_ITEMS[item_clean]
    role = discord.utils.find(lambda r: r.name.lower() == item_clean, ctx.guild.roles)
    if not role: return await ctx.send("⚠️ Rôle Discord introuvable.")
    if role in ctx.author.roles: return await ctx.send("❌ Déjà possédé.")
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    
    try:
        db[uid] -= price; save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"🎉 Tu as acheté **{role.name}** !")
    except: await ctx.send("❌ Permission refusée.")

@bot.command()
async def help(ctx):
    em = discord.Embed(title="Aide Pandora", color=0x4b41e6)
    em.add_field(name="💰 Gains", value="`!work`, `!daily`, `!rob`", inline=True)
    em.add_field(name="🎲 Jeux", value="`!roulette`, `!blackjack`, `!morpion`", inline=True)
    em.add_field(name="💳 Banque", value="`!bal`, `!give`, `!shop`, `!buy`", inline=False)
    await ctx.send(embed=em)

# --- 9. LANCEMENT ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown : {int(error.retry_after)}s.", delete_after=5)

keep_alive()
bot.run(os.environ.get('TOKEN'))
