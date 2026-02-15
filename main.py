import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR HEBERGER GRATUITEMENT) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino est en ligne et fonctionnel !"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES & UTILITAIRES ---
DB_FILE = "database.json"

# Couleurs des Embeds
COL_GOLD = 0xFFD700   # Argent / Gains
COL_RED = 0xFF0033    # Erreurs / Pertes
COL_GREEN = 0x00FF00  # Succès
COL_BLUE = 0x4B41E6   # Info / Casino
COL_DARK = 0x2C2F33   # Background

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def parse_amount(amount_str, balance):
    """Gère 'all', 'tout' ou un montant précis."""
    if str(amount_str).lower() in ["all", "tout"]:
        return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. CONFIGURATION DU BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ⚠️ REMPLACE CES ID PAR CEUX DE TON SERVEUR ⚠️
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914

# CONFIGURATION JEUX
SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 20, 15, 8, 2] 

# VARIABLES GLOBALES
race_open = False
race_bets = [] 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora Casino est connecté en tant que {bot.user} !")
    await bot.change_presence(activity=discord.Game(name="!help | 🎰 Casino"))

# --- 4. BIENVENUE & DÉPART (STABILISÉ) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return

    file_path = "static/images/background.gif"
    desc = f"Bienvenue {member.mention} (**{member.display_name}**) !\nAmuse-toi bien au **Pandora Casino** 🎰"
    
    embed = discord.Embed(title="👋 Nouveau Membre !", description=desc, color=COL_BLUE)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"Nous sommes maintenant {len(member.guild.members)} membres")

    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(embed=embed, file=file)
        except:
            await channel.send(embed=embed) # Envoie sans image si erreur fichier
    else:
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if not channel: return

    file_path = "static/images/leave.gif"
    desc = f"**{member.display_name}** a quitté le casino..."
    
    embed = discord.Embed(description=desc, color=COL_RED)
    
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="leave.gif")
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)
        except:
            await channel.send(embed=embed)
    else:
        await channel.send(embed=embed)

# --- 5. COMMANDE HELP (Améliorée) ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🎰 PANDORA CASINO - AIDE", description="Bienvenue au casino ! Voici les commandes disponibles.", color=COL_GOLD)
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    # Catégorie Économie
    embed.add_field(
        name="💰 Économie", 
        value="`!bal` : Voir son solde\n`!work` : Travailler (10 min)\n`!daily` : Bonus quotidien (1000-3000)\n`!rob @user` : Voler un joueur\n`!give @user <montant/all>` : Donner", 
        inline=False
    )

    # Catégorie Casino
    embed.add_field(
        name="🎰 Jeux de Hasard", 
        value="`!slot <mise>` : Machine à sous\n`!blackjack <mise>` : Le 21\n`!roulette <mise> <choix>` : Rouge ou Noir\n`!dice <mise>` : Duel de dés", 
        inline=False
    )

    # Catégorie Duel & Multi
    embed.add_field(
        name="👥 Duels & Courses", 
        value="`!morpion @user <mise>` : Duel de Tic-Tac-Toe\n`!race` : Lancer une course de chevaux\n`!bet <mise> <cheval>` : Parier sur la course", 
        inline=False
    )

    # Catégorie Autre
    embed.add_field(
        name="🛒 Divers", 
        value="`!shop` : Boutique de rôles\n`!buy <item>` : Acheter un objet\n`!top` : Classement des riches", 
        inline=False
    )
    
    embed.set_footer(text="Pandora Casino • Pariez responsable (ou pas) !")
    await ctx.send(embed=embed)

# --- 6. ÉCONOMIE ---

@bot.command(aliases=["top", "rich"])
async def leaderboard(ctx):
    db = load_db()
    users = [(k, v) for k, v in db.items() if k.isdigit() and isinstance(value := v, int)]
    users.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 CLASSEMENT DES RICHES", color=COL_GOLD)
    desc = ""
    for idx, (uid, bal) in enumerate(users[:5], 1):
        user = bot.get_user(int(uid))
        name = user.display_name if user else "Inconnu"
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        desc += f"**{medal} {name}** • {bal:,} coins\n"
    
    embed.description = desc if desc else "Personne n'a d'argent..."
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    db = load_db()
    amount = db.get(str(target.id), 0)
    
    embed = discord.Embed(title="💳 Portefeuille", color=COL_BLUE)
    embed.set_author(name=target.display_name, icon_url=target.avatar.url if target.avatar else None)
    embed.description = f"Solde actuel : **{amount:,} coins**"
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user) # 10 MINUTES
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 500)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    
    embed = discord.Embed(description=f"🔨 Tu as travaillé dur et gagné **{gain} coins** !", color=COL_GREEN)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_last_daily"
    
    # 12 heures = 43200 secondes
    if time.time() - db.get(key, 0) < 43200: 
        remaining = 43200 - (time.time() - db.get(key, 0))
        h, rem = divmod(remaining, 3600)
        m, s = divmod(rem, 60)
        return await ctx.send(embed=discord.Embed(description=f"⏳ Reviens dans **{int(h)}h {int(m)}m**.", color=COL_RED))
    
    gain = random.randint(1000, 3000) # GAIN AUGMENTÉ
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    
    embed = discord.Embed(title="🎁 Bonus Quotidien", description=f"Tu as reçu **{gain} coins** !", color=COL_GOLD)
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member.id == ctx.author.id: return
    db = load_db()
    uid, tid = str(ctx.author.id), str(member.id)
    bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount: 
        return await ctx.send(embed=discord.Embed(description="❌ Montant invalide ou fonds insuffisants.", color=COL_RED))
    
    db[uid] -= amount
    db[tid] = db.get(tid, 0) + amount
    save_db(db)
    
    await ctx.send(embed=discord.Embed(description=f"💸 **{ctx.author.display_name}** a envoyé **{amount} coins** à **{member.display_name}**.", color=COL_GREEN))

@bot.command()
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    
    if v_bal < 500: return await ctx.send(embed=discord.Embed(description="❌ Ce joueur est trop pauvre pour être volé.", color=COL_RED))
    
    if random.choice([True, False]): # 50% de chance
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] += stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"🥷 Tu as volé **{stolen} coins** à {member.display_name} !", color=COL_GREEN))
    else:
        fine = 200
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"👮 Tu t'es fait attraper ! Amende de **{fine} coins**.", color=COL_RED))

# --- 7. JEUX DE CASINO ---

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount: 
        return await ctx.send(embed=discord.Embed(description="❌ Pas assez d'argent.", color=COL_RED))
    
    p_roll = [random.randint(1, 6), random.randint(1, 6)]
    b_roll = [random.randint(1, 6), random.randint(1, 6)]
    
    embed = discord.Embed(title="🎲 Duel de Dés", color=COL_BLUE)
    embed.add_field(name=f"Toi", value=f"🎲 {p_roll[0]} + {p_roll[1]} = **{sum(p_roll)}**", inline=True)
    embed.add_field(name=f"Bot", value=f"🎲 {b_roll[0]} + {b_roll[1]} = **{sum(b_roll)}**", inline=True)
    
    if sum(p_roll) > sum(b_roll):
        db[uid] += amount
        embed.color = COL_GREEN
        embed.description = f"🎉 **Victoire !** Tu gagnes {amount} coins."
    elif sum(p_roll) < sum(b_roll):
        db[uid] -= amount
        embed.color = COL_RED
        embed.description = f"❌ **Défaite...** Tu perds {amount} coins."
    else:
        embed.description = "🤝 **Égalité.** Mise remboursée."
    
    save_db(db)
    await ctx.send(embed=embed)

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount: 
        return await ctx.send(embed=discord.Embed(description="❌ Pas assez d'argent.", color=COL_RED))
    
    items = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    multiplier = 0
    
    # Logique de gain
    if items[0] == items[1] == items[2]:
        if items[0] == "7️⃣": multiplier = 100
        elif items[0] == "💎": multiplier = 50
        elif items[0] == "🔔": multiplier = 20
        else: multiplier = 10
    elif items[0] == items[1] or items[1] == items[2] or items[0] == items[2]:
        multiplier = 1.5

    result_display = f"🔹 ┃ {items[0]} ┃ {items[1]} ┃ {items[2]} ┃ 🔹"

    if multiplier > 0:
        win = int(amount * multiplier)
        profit = win - amount
        db[uid] = db.get(uid, 0) + profit
        
        # Streak Hakari
        streak = db.get(f"{uid}_slot_streak", 0) + 1
        db[f"{uid}_slot_streak"] = streak
        extra = ""
        if streak >= 7:
             role = discord.utils.get(ctx.guild.roles, name="Hakari")
             if role and role not in ctx.author.roles:
                 await ctx.author.add_roles(role)
                 extra = "\n🕺 **JACKPOT ! Tu es maintenant HAKARI !**"
        
        embed = discord.Embed(title="🎰 Machine à sous", description=f"{result_display}\n\n✅ **GAGNÉ !** +{profit} coins{extra}", color=COL_GREEN)
    else:
        db[uid] -= amount
        db[f"{uid}_slot_streak"] = 0
        embed = discord.Embed(title="🎰 Machine à sous", description=f"{result_display}\n\n❌ **PERDU...**", color=COL_RED)

    save_db(db)
    await ctx.send(embed=embed)

# --- BLACKJACK (STABLE) ---
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=60)
        self.author_id, self.amount, self.db = author_id, amount, db
        self.deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
        self.player = [self.draw(), self.draw()]
        self.dealer = [self.draw(), self.draw()]
        
    def draw(self): return random.choice(self.deck)
    def calc(self, hand):
        s = sum(hand); aces = hand.count(11)
        while s > 21 and aces: s-=10; aces-=1
        return s

    async def update(self, interaction, end=False, msg="", color=COL_BLUE):
        embed = discord.Embed(title="🃏 Blackjack", description=msg, color=color)
        embed.add_field(name=f"Toi ({self.calc(self.player)})", value=str(self.player))
        if end:
            embed.add_field(name=f"Croupier ({self.calc(self.dealer)})", value=str(self.dealer))
            for c in self.children: c.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed.add_field(name="Croupier", value=f"[{self.dealer[0]}, ?]")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, interaction, button):
        if interaction.user.id != self.author_id: return
        self.player.append(self.draw())
        if self.calc(self.player) > 21:
            await self.update(interaction, True, "💥 **Tu as sauté !**", COL_RED)
        else:
            await self.update(interaction)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction, button):
        if interaction.user.id != self.author_id: return
        while self.calc(self.dealer) < 17: self.dealer.append(self.draw())
        
        p, d = self.calc(self.player), self.calc(self.dealer)
        uid = str(self.author_id)
        
        if d > 21:
            self.db[uid] += self.amount * 2
            await self.update(interaction, True, "🎉 **Croupier saute ! Tu gagnes.**", COL_GREEN)
        elif p > d:
            self.db[uid] += self.amount * 2
            await self.update(interaction, True, "🎉 **Tu gagnes !**", COL_GREEN)
        elif p == d:
            self.db[uid] += self.amount
            await self.update(interaction, True, "🤝 **Égalité.**", COL_GOLD)
        else:
            await self.update(interaction, True, "❌ **Perdu.**", COL_RED)
        save_db(self.db)

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    if amount <= 0 or bal < amount: return await ctx.send(embed=discord.Embed(description="❌ Pas assez d'argent.", color=COL_RED))
    
    db[uid] -= amount
    save_db(db)
    
    view = BlackjackView(ctx.author.id, amount, db)
    embed = discord.Embed(title="🃏 Blackjack", color=COL_BLUE)
    embed.add_field(name=f"Toi ({view.calc(view.player)})", value=str(view.player))
    embed.add_field(name="Croupier", value=f"[{view.dealer[0]}, ?]")
    await ctx.send(embed=embed, view=view)

# --- MORPION (DUEL) ---
class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2, amount, db):
        super().__init__(); self.p1, self.p2, self.amt, self.db = p1, p2, amount, db
        self.turn = p1; self.board = [0]*9
        for i in range(9): self.add_item(TicTacToeButton(i))

    def check_win(self):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if self.board[a] == self.board[b] == self.board[c] != 0: return True
        return False

class TicTacToeButton(discord.ui.Button):
    def __init__(self, idx):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=idx//3)
        self.idx = idx

    async def callback(self, interaction):
        view = self.view
        if interaction.user != view.turn: return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        if self.label != "⬜": return
        
        token = "❌" if view.turn == view.p1 else "⭕"
        self.style = discord.ButtonStyle.danger if view.turn == view.p1 else discord.ButtonStyle.success
        self.label = token
        self.disabled = True
        view.board[self.idx] = 1 if view.turn == view.p1 else 2
        
        if view.check_win():
            win_amt = view.amt * 2
            if view.amt > 0:
                view.db[str(view.turn.id)] += win_amt
                save_db(view.db)
            
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{view.turn.display_name} remporte la partie !** (+{win_amt} coins)", view=view)
            view.stop()
        elif 0 not in view.board:
            if view.amt > 0:
                view.db[str(view.p1.id)] += view.amt
                view.db[str(view.p2.id)] += view.amt
                save_db(view.db)
            await interaction.response.edit_message(content="🤝 **Match nul !** (Remboursé)", view=view)
            view.stop()
        else:
            view.turn = view.p2 if view.turn == view.p1 else view.p1
            await interaction.response.edit_message(content=f"Au tour de : {view.turn.mention}", view=view)

class DuelReqView(discord.ui.View):
    def __init__(self, p1, p2, amt):
        super().__init__(timeout=60); self.p1, self.p2, self.amt = p1, p2, amt
    
    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        if interaction.user != self.p2: return
        db = load_db()
        if db.get(str(self.p2.id),0) < self.amt: return await interaction.response.send_message("Pas assez d'argent !", ephemeral=True)
        if db.get(str(self.p1.id),0) < self.amt: return await interaction.response.send_message("L'adversaire n'a plus assez d'argent !", ephemeral=True)
        
        if self.amt > 0:
            db[str(self.p1.id)] -= self.amt
            db[str(self.p2.id)] -= self.amt
            save_db(db)
            
        await interaction.response.edit_message(content=f"✅ **Duel lancé !** Mise : {self.amt}", view=None)
        await interaction.channel.send(f"🎮 {self.p1.mention} vs {self.p2.mention}", view=TicTacToeView(self.p1, self.p2, self.amt, db))

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction, button):
        if interaction.user != self.p2: return
        await interaction.response.edit_message(content="❌ Duel refusé.", view=None)

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str="0"):
    if member.bot or member == ctx.author: return
    db = load_db(); bal = db.get(str(ctx.author.id), 0)
    amount = parse_amount(amount_str, bal)
    
    if amount > 0 and bal < amount: return await ctx.send(embed=discord.Embed(description="❌ Pas assez d'argent.", color=COL_RED))
    
    await ctx.send(f"⚔️ {member.mention}, **{ctx.author.display_name}** te défie au Morpion pour **{amount} coins** !", view=DuelReqView(ctx.author, member, amount))

# --- COURSES (RACE) ---
@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return await ctx.send("🏇 Course déjà en cours !")
    
    race_open = True
    race_bets = []
    
    embed = discord.Embed(title="🏇 HIPPODROME PANDORA", description="Départ dans **30 secondes** !\nTape `!bet <mise> <cheval 1-5>`", color=COL_GREEN)
    embed.set_image(url="https://media.tenor.com/On7kvX5F2Q4AAAAM/horse-racing.gif") # Un gif pour le style
    await ctx.send(embed=embed)
    
    await asyncio.sleep(30)
    
    if not race_bets:
        race_open = False
        return await ctx.send("❌ Course annulée (aucun pari).")
    
    msg = await ctx.send("🏁 **C'est parti !**")
    
    # Animation
    track = ["🏇", "🏇", "🏇", "🏇", "🏇"]
    for i in range(3):
        await asyncio.sleep(1.5)
        random.shuffle(track) # Mélange juste visuel
        desc = ""
        for idx, horse in enumerate(track, 1):
            desc += f"{idx}. {horse} {'💨' if random.random()>0.6 else ''}\n"
        await msg.edit(embed=discord.Embed(title="🏇 La course est folle !", description=desc, color=COL_GOLD))
    
    winner = random.randint(1, 5)
    db = load_db()
    txt_res = f"👑 **Le Cheval #{winner} l'emporte !**\n\n"
    
    found_winner = False
    for b in race_bets:
        if b['horse'] == winner:
            found_winner = True
            gain = b['amount'] * 2
            db[str(b['uid'])] = db.get(str(b['uid']), 0) + gain
            
            # Gestion Role Dompteur
            k_win = f"{b['uid']}_race_wins"
            db[k_win] = db.get(k_win, 0) + 1
            if db[k_win] == 10:
                user = ctx.guild.get_member(b['uid'])
                role = discord.utils.get(ctx.guild.roles, name="Dompteur de chevaux")
                if user and role: await user.add_roles(role)

            txt_res += f"✅ <@{b['uid']}> gagne **{gain} coins** !\n"
    
    if not found_winner: txt_res += "❌ Personne n'a parié sur le gagnant."
    
    save_db(db)
    race_open = False
    race_bets = []
    
    await ctx.send(embed=discord.Embed(description=txt_res, color=COL_GOLD))

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_open, race_bets
    if not race_open: return await ctx.send("❌ Pas de course en cours.")
    if not (1 <= horse <= 5): return await ctx.send("❌ Cheval invalide (1-5).")
    
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount: return await ctx.send("❌ Mise invalide.")
    for b in race_bets:
        if b['uid'] == ctx.author.id: return await ctx.send("❌ Tu as déjà parié.")

    db[uid] -= amount
    save_db(db)
    race_bets.append({'uid': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"🎟️ Mise de **{amount}** acceptée sur le cheval **#{horse}**.")

# --- BOUTIQUE ---
@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 BOUTIQUE", color=COL_BLUE)
    for name, price in SHOP_ITEMS.items():
        embed.add_field(name=name.capitalize(), value=f"💰 {price:,} coins", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item_name: str):
    db = load_db(); uid = str(ctx.author.id); item_name = item_name.lower()
    if item_name not in SHOP_ITEMS: return await ctx.send("❌ Article inconnu.")
    
    price = SHOP_ITEMS[item_name]
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    
    role = discord.utils.find(lambda r: r.name.lower() == item_name, ctx.guild.roles)
    if not role: return await ctx.send("❌ Rôle introuvable sur le serveur (vérifiez les noms).")
    
    try:
        await ctx.author.add_roles(role)
        db[uid] -= price
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"✅ Tu as acheté **{role.name}** !", color=COL_GREEN))
    except:
        await ctx.send("❌ Je n'ai pas la permission de donner ce rôle (vérifiez mes droits).")

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"✅ **{amount} coins** donnés à {member.display_name}.")

# --- GESTION DES ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        await ctx.send(embed=discord.Embed(description=f"⏳ Patiente encore **{int(m)}m {int(s)}s**.", color=COL_RED), delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(description="❌ Commande incomplète. Vérifie `!help`.", color=COL_RED), delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(description="❌ Argument invalide (ex: il faut un nombre).", color=COL_RED), delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass # On ignore les commandes inconnues
    else:
        print(f"Erreur : {error}")

keep_alive()
bot.run(os.environ.get('TOKEN'))
