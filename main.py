import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR LE WEB) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino est en ligne et sauvegarde les données !"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. GESTION BASE DE DONNÉES (PERSISTANCE) ---
DB_FILE = "database.json"

# Couleurs Embeds
COL_GOLD = 0xFFD700
COL_RED = 0xFF0033
COL_GREEN = 0x00FF00
COL_BLUE = 0x4B41E6

def load_db():
    """Charge la base de données. Crée le fichier s'il n'existe pas."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # En cas de fichier corrompu, on retourne une base vide pour ne pas crash
        return {}

def save_db(data):
    """Sauvegarde immédiate pour éviter les pertes."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def parse_amount(amount_str, balance):
    """Gère 'all' ou un nombre."""
    if str(amount_str).lower() in ["all", "tout"]:
        return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ⚠️ METS TES ID DE SALONS ICI ⚠️
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
    print(f"✅ Pandora Casino connecté en tant que {bot.user} !")
    print(f"✅ Données chargées : {len(load_db())} comptes.")
    await bot.change_presence(activity=discord.Game(name="!help | 🎰 Casino"))

# --- 4. BIENVENUE & DÉPART ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    file_path = "static/images/background.gif"
    desc = f"Bienvenue {member.mention} (**{member.display_name}**) !\nInstalle-toi et tente de devenir le **Jockey Genius** ou le **Hakari** du serveur ! 🎰"
    embed = discord.Embed(title="👋 Nouveau Parieur !", description=desc, color=COL_BLUE)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(embed=embed, file=file)
        except: await channel.send(embed=embed)
    else: await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if not channel: return
    file_path = "static/images/leave.gif"
    embed = discord.Embed(description=f"**{member.display_name}** a fait banqueroute et nous quitte...", color=COL_RED)
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="leave.gif")
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)
        except: await channel.send(embed=embed)
    else: await channel.send(embed=embed)

# --- 5. HELP COMPLET ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🎰 PANDORA CASINO - GUIDE", description="Voici toutes les commandes pour devenir riche !", color=COL_GOLD)
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    # ÉCONOMIE
    embed.add_field(
        name="💰 __Économie__", 
        value="**`!bal`** : Voir ton solde.\n**`!work`** : Travailler (Cooldown 10min).\n**`!daily`** : Cadeau quotidien (1k-3k).\n**`!give @user <montant>`** : Faire un don.\n**`!rob @user`** : Voler (Risqué !).\n**`!top`** : Classement des riches.", 
        inline=False
    )

    # CASINO
    embed.add_field(
        name="🎲 __Jeux & Casino__", 
        value="**`!slot <mise>`** : Machine à sous.\n> *🔥 7 victoires d'affilée = Rôle Hakari*\n**`!blackjack <mise>`** : Le célèbre 21.\n**`!roulette <mise> <rouge/noir>`** : Double ou rien.\n**`!dice <mise>`** : Duel de dés contre le bot.", 
        inline=False
    )

    # MULTIJOUEUR
    embed.add_field(
        name="🏇 __Courses & Duels__", 
        value="**`!race`** : Lancer une course de chevaux.\n**`!bet <mise> <cheval>`** : Parier sur la course.\n> *🏅 10 victoires = Rôle Jockey Genius*\n**`!morpion @user <mise>`** : Duel de Tic-Tac-Toe.", 
        inline=False
    )

    # ADMIN & BOUTIQUE
    embed.add_field(
        name="👮 __Staff & Boutique__", 
        value="**`!shop`** : Voir les articles.\n**`!buy <item>`** : Acheter un rôle.\n**`!admingive @user <montant>`** : (Admin) Créer de l'argent.\n**`!tax @user <montant>`** : (Admin) Taxer un joueur.", 
        inline=False
    )

    embed.set_footer(text="Astuce : Tu peux écrire 'all' à la place du montant pour tout miser !")
    await ctx.send(embed=embed)


# --- 6. ÉCONOMIE & ADMIN ---

@bot.command(aliases=["top", "richest"])
async def leaderboard(ctx):
    db = load_db()
    # On filtre pour ne garder que les ID numériques (les vrais joueurs)
    users = [(k, v) for k, v in db.items() if k.isdigit() and isinstance(v, int)]
    users.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 TOP 5 RICHESSE", color=COL_GOLD)
    desc = ""
    for idx, (uid, bal) in enumerate(users[:5], 1):
        user = bot.get_user(int(uid))
        name = user.display_name if user else "Inconnu"
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        desc += f"**{medal} {name}** • {bal:,} coins\n"
    
    embed.description = desc if desc else "La banque est vide..."
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user) # 10 minutes
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 500)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"🔨 Tu as travaillé et gagné **{gain} coins**.", color=COL_GREEN))

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_daily"
    # 12 heures
    if time.time() - db.get(key, 0) < 43200:
        rem = 43200 - (time.time() - db.get(key, 0))
        h, rem = divmod(rem, 3600); m, s = divmod(rem, 60)
        return await ctx.send(embed=discord.Embed(description=f"⏳ Reviens dans **{int(h)}h {int(m)}m**.", color=COL_RED))
    
    gain = random.randint(1000, 3000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"🎁 Cadeau quotidien : **+{gain} coins** !", color=COL_GOLD))

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member == ctx.author: return
    db = load_db(); uid, tid = str(ctx.author.id), str(member.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    db[uid] -= amount; db[tid] = db.get(tid, 0) + amount
    save_db(db)
    await ctx.send(f"💸 **{ctx.author.display_name}** donne **{amount}** à **{member.display_name}**.")

@bot.command()
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    if v_bal < 500: return await ctx.send("❌ Trop pauvre pour être volé.")
    
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal*0.05), int(v_bal*0.20))
        db[str(ctx.author.id)] += stolen; db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(f"🥷 Vol réussi ! Tu as pris **{stolen}** !")
    else:
        fine = 200
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(f"👮 Arrêté par la police ! Amende : **-{fine}**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"✅ **ADMIN :** {amount} ajoutés à {member.mention}.", color=COL_GREEN))

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    bal = db.get(uid, 0)
    
    if bal <= 0: return await ctx.send("❌ Ce joueur est déjà à 0.")
    to_remove = min(amount, bal)
    db[uid] -= to_remove
    save_db(db)
    
    embed = discord.Embed(title="⚖️ Taxe Fiscale", description=f"L'admin a prélevé **{to_remove} coins** sur le compte de {member.mention}.", color=COL_RED)
    embed.set_footer(text=f"Nouveau solde : {db[uid]}")
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx, member: discord.Member = None):
    t = member if member else ctx.author; db = load_db()
    await ctx.send(embed=discord.Embed(description=f"💰 Solde de **{t.display_name}** : `{db.get(str(t.id), 0)}` coins", color=COL_BLUE))

# --- 7. JEUX ---

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    items = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    mult = 0
    
    # Calculs gains
    if items[0] == items[1] == items[2]:
        if items[0] == "7️⃣": mult = 100
        elif items[0] == "💎": mult = 50
        elif items[0] == "🔔": mult = 20
        else: mult = 10
    elif items[0] == items[1] or items[1] == items[2] or items[0] == items[2]:
        mult = 1.5
        
    display = f"🔹 ┃ {items[0]} ┃ {items[1]} ┃ {items[2]} ┃ 🔹"
    streak_key = f"{uid}_slot_streak"
    
    if mult > 0:
        win = int(amount * mult); profit = win - amount
        db[uid] = db.get(uid, 0) + profit
        
        # GESTION HAKARI (7 wins d'affilée)
        current_streak = db.get(streak_key, 0) + 1
        db[streak_key] = current_streak
        
        streak_msg = f"\n🔥 Win Streak : {current_streak}/7"
        if current_streak >= 7:
            role = discord.utils.get(ctx.guild.roles, name="Hakari")
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                streak_msg += "\n🕺 **JACKPOT ! Tu reçois le rôle HAKARI !**"
        
        embed = discord.Embed(title="🎰 Machine à sous", description=f"{display}\n\n✅ **GAGNÉ !** +{profit} coins{streak_msg}", color=COL_GREEN)
    else:
        db[uid] -= amount
        db[streak_key] = 0 # Reset streak
        embed = discord.Embed(title="🎰 Machine à sous", description=f"{display}\n\n❌ **PERDU...**", color=COL_RED)
        
    save_db(db)
    await ctx.send(embed=embed)

@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return await ctx.send("🏇 Une course est déjà en cours.")
    
    race_open = True; race_bets = []
    embed = discord.Embed(title="🏇 Hippodrome", description="Départ dans **30s** !\n`!bet <mise> <cheval 1-5>`", color=COL_GREEN)
    await ctx.send(embed=embed)
    
    await asyncio.sleep(30)
    if not race_bets:
        race_open = False; return await ctx.send("❌ Course annulée (0 pari).")
    
    msg = await ctx.send("🏁 **C'est parti !**")
    track = ["🏇"] * 5
    for i in range(3):
        await asyncio.sleep(1.5)
        res_anim = ""
        for j in range(5): res_anim += f"{j+1}. {track[j]} {'💨' if random.random()>0.5 else ''}\n"
        await msg.edit(embed=discord.Embed(title="🏇 En course...", description=res_anim, color=COL_GOLD))
        
    winner = random.randint(1, 5)
    db = load_db()
    txt = f"👑 **Victoire du Cheval #{winner} !**\n\n"
    
    found = False
    for b in race_bets:
        if b['horse'] == winner:
            found = True
            win = b['amount'] * 2
            uid = b['uid']
            db[str(uid)] = db.get(str(uid), 0) + win
            
            # GESTION JOCKEY GENIUS (10 victoires)
            w_key = f"{uid}_race_wins"
            db[w_key] = db.get(w_key, 0) + 1
            
            if db[w_key] >= 10:
                user = ctx.guild.get_member(uid)
                role = discord.utils.get(ctx.guild.roles, name="Jockey Genius")
                if user and role and role not in user.roles:
                    await user.add_roles(role)
                    txt += f"🏅 <@{uid}> devient **Jockey Genius** !\n"
            
            txt += f"✅ <@{uid}> gagne {win} coins !\n"
            
    if not found: txt += "❌ Personne n'a gagné."
    
    save_db(db)
    race_open = False; race_bets = []
    await ctx.send(embed=discord.Embed(description=txt, color=COL_GOLD))

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_open, race_bets
    if not race_open: return await ctx.send("❌ Pas de course.")
    if not (1<=horse<=5): return await ctx.send("❌ Cheval 1 à 5.")
    
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Mise invalide.")
    for b in race_bets:
        if b['uid'] == ctx.author.id: return await ctx.send("❌ Déjà parié.")
        
    db[uid] -= amount; save_db(db)
    race_bets.append({'uid': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"🎟️ Pari accepté sur le **#{horse}** !")

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    p = sum([random.randint(1,6) for _ in range(2)])
    b = sum([random.randint(1,6) for _ in range(2)])
    
    embed = discord.Embed(title="🎲 Dés", color=COL_BLUE)
    embed.add_field(name="Toi", value=str(p)); embed.add_field(name="Bot", value=str(b))
    
    if p > b:
        db[uid] += amount; save_db(db)
        embed.color = COL_GREEN; embed.description = f"🎉 **Gagné !** +{amount}"
    elif p < b:
        db[uid] -= amount; save_db(db)
        embed.color = COL_RED; embed.description = f"❌ **Perdu...** -{amount}"
    else:
        embed.description = "🤝 **Égalité.**"
    await ctx.send(embed=embed)

# --- BLACKJACK ---
class BlackjackView(discord.ui.View):
    def __init__(self, uid, amt, db):
        super().__init__(timeout=60); self.uid, self.amt, self.db = uid, amt, db
        self.deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
        self.p = [self.draw(), self.draw()]; self.d = [self.draw(), self.draw()]
    def draw(self): return random.choice(self.deck)
    def calc(self, h):
        s=sum(h); a=h.count(11)
        while s>21 and a: s-=10; a-=1
        return s
    async def end(self, i, msg, col):
        e = discord.Embed(title="Blackjack", description=msg, color=col)
        e.add_field(name=f"Toi ({self.calc(self.p)})", value=str(self.p))
        e.add_field(name=f"Croupier ({self.calc(self.d)})", value=str(self.d))
        for c in self.children: c.disabled=True
        await i.response.edit_message(embed=e, view=self)
    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, i, b):
        if i.user.id != self.uid: return
        self.p.append(self.draw())
        if self.calc(self.p)>21: await self.end(i, "💥 Sauté !", COL_RED)
        else:
            e = discord.Embed(title="Blackjack", color=COL_BLUE)
            e.add_field(name=f"Toi ({self.calc(self.p)})", value=str(self.p))
            e.add_field(name="Croupier", value=f"[{self.d[0]}, ?]")
            await i.response.edit_message(embed=e, view=self)
    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, i, b):
        if i.user.id != self.uid: return
        while self.calc(self.d)<17: self.d.append(self.draw())
        pv, dv = self.calc(self.p), self.calc(self.d)
        uid = str(self.uid)
        if dv>21: self.db[uid]+=self.amt*2; await self.end(i, "🎉 Croupier saute !", COL_GREEN)
        elif pv>dv: self.db[uid]+=self.amt*2; await self.end(i, "🎉 Gagné !", COL_GREEN)
        elif pv==dv: self.db[uid]+=self.amt; await self.end(i, "🤝 Égalité.", COL_GOLD)
        else: await self.end(i, "❌ Perdu.", COL_RED)
        save_db(self.db)

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    db[uid] -= amount; save_db(db)
    v = BlackjackView(ctx.author.id, amount, db)
    e = discord.Embed(title="Blackjack", color=COL_BLUE)
    e.add_field(name=f"Toi ({v.calc(v.p)})", value=str(v.p))
    e.add_field(name="Croupier", value=f"[{v.d[0]}, ?]")
    await ctx.send(embed=e, view=v)

# --- MORPION ---
class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2, amt, db):
        super().__init__(); self.p1, self.p2, self.amt, self.db = p1, p2, amt, db
        self.turn = p1; self.board = [0]*9
        for i in range(9): self.add_item(TicTacToeButton(i))
    def check(self):
        w = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(self.board[a]==self.board[b]==self.board[c]!=0 for a,b,c in w)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, i): super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=i//3); self.idx = i
    async def callback(self, i):
        v = self.view
        if i.user != v.turn: return await i.response.send_message("Pas ton tour !", ephemeral=True)
        if self.label != "⬜": return
        self.style = discord.ButtonStyle.danger if v.turn == v.p1 else discord.ButtonStyle.success
        self.label = "❌" if v.turn == v.p1 else "⭕"; self.disabled = True
        v.board[self.idx] = 1 if v.turn == v.p1 else 2
        
        if v.check():
            if v.amt > 0: v.db[str(v.turn.id)] += v.amt * 2; save_db(v.db)
            for c in v.children: c.disabled = True
            await i.response.edit_message(content=f"🏆 **{v.turn.display_name} gagne !**", view=v); v.stop()
        elif 0 not in v.board:
            if v.amt > 0: v.db[str(v.p1.id)] += v.amt; v.db[str(v.p2.id)] += v.amt; save_db(v.db)
            await i.response.edit_message(content="🤝 Match nul.", view=v); v.stop()
        else:
            v.turn = v.p2 if v.turn == v.p1 else v.p1
            await i.response.edit_message(content=f"Tour de {v.turn.mention}", view=v)

class DuelReq(discord.ui.View):
    def __init__(self, p1, p2, amt): super().__init__(timeout=60); self.p1,self.p2,self.amt = p1,p2,amt
    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def ok(self, i, b):
        if i.user != self.p2: return
        db = load_db()
        if db.get(str(self.p2.id),0) < self.amt or db.get(str(self.p1.id),0) < self.amt: return await i.response.send_message("Erreur fonds.", ephemeral=True)
        if self.amt > 0: db[str(self.p1.id)] -= self.amt; db[str(self.p2.id)] -= self.amt; save_db(db)
        await i.response.edit_message(content=f"✅ Duel lancé ! Mise : {self.amt}", view=None)
        await i.channel.send(view=TicTacToeView(self.p1, self.p2, self.amt, db))

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str="0"):
    if member.bot or member==ctx.author: return
    db = load_db(); amt = parse_amount(amount_str, db.get(str(ctx.author.id), 0))
    if amt > 0 and db.get(str(ctx.author.id), 0) < amt: return await ctx.send("❌ Pas assez d'argent.")
    await ctx.send(f"⚔️ {member.mention}, défi Morpion pour **{amt}** ?", view=DuelReq(ctx.author, member, amt))

# --- BOUTIQUE ---
@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 Boutique", color=COL_BLUE)
    for k,v in SHOP_ITEMS.items(): e.add_field(name=k, value=f"{v} coins", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db(); uid = str(ctx.author.id); item = item.lower()
    if item not in SHOP_ITEMS: return await ctx.send("❌ Inconnu.")
    price = SHOP_ITEMS[item]
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if not role: return await ctx.send("❌ Rôle introuvable.")
    try: await ctx.author.add_roles(role); db[uid] -= price; save_db(db); await ctx.send(f"✅ Acheté : **{role.name}** !")
    except: await ctx.send("❌ Permission insuffisante.")

# --- ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        await ctx.send(embed=discord.Embed(description=f"⏳ Patiente **{int(m)}m {int(s)}s**.", color=COL_RED), delete_after=5)

keep_alive()
bot.run(os.environ.get('TOKEN'))
