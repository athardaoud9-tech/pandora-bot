import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Pandora Casino est en ligne (vFinal) !"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURATION ---
DB_FILE = "database.json"
TAX_RATE = 0.05 # 5% de taxe

# Couleurs
COL_GOLD = 0xFFD700
COL_RED = 0xE74C3C
COL_GREEN = 0x2ECC71
COL_BLUE = 0x3498DB
COL_DARK = 0x2C3E50

# Configuration Bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ⚠️ TES ID DE SALONS
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914

# 🛒 BOUTIQUE
SHOP_ITEMS = {
    "juif": 10000,       # Peut voler (rob)
    "riche": 100000,
    "roi": 1000000
}

# --- 3. FONCTIONS UTILES ---
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

def parse_amount(amount_str, balance):
    if str(amount_str).lower() in ["all", "tout"]: return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except: return 0

# --- 4. ÉVÉNEMENTS (BIENVENUE / BYE) ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name="!helpme | Casino Pro"))

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="👋 Bienvenue !", description=f"Bienvenue {member.mention} sur le serveur !", color=COL_GREEN)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"Nous sommes {len(member.guild.members)} membres")
    
    file_path = "static/images/background.gif"
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
    embed = discord.Embed(description=f"**{member.display_name}** est parti...", color=COL_DARK)
    file_path = "static/images/leave.gif"
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="leave.gif")
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)
        except: await channel.send(embed=embed)
    else: await channel.send(embed=embed)

# --- 5. COMMANDE HELPME COMPLET ---
@bot.command()
async def helpme(ctx):
    embed = discord.Embed(title="📜 MENU PRINCIPAL - PANDORA CASINO", description="Voici toutes les commandes disponibles pour devenir riche !", color=COL_GOLD)
    
    embed.add_field(name="💰 __Économie de base__", value=(
        "**`!bal`** : Voir ton solde actuel.\n"
        "**`!work`** : Travailler (Gain: 200-800 | Cooldown: 10m).\n"
        "**`!daily`** : Cadeau journalier (Gain: 1k-3k | Cooldown: 24h).\n"
        "**`!give @user <montant>`** : Donner de l'argent (Taxe 5%).\n"
        "**`!top`** : Voir le classement des plus riches."
    ), inline=False)

    embed.add_field(name="😈 __Crime & Vol__", value=(
        "**`!rob @user`** : Voler un membre.\n"
        "> ⚠️ **Requis :** Avoir le rôle 'Juif'.\n"
        "> ⏳ **Cooldown :** 20 minutes.\n"
        "> 🎲 **Risque :** 50% de chance de réussite."
    ), inline=False)

    embed.add_field(name="🎰 __Jeux de Casino (Boostés)__", value=(
        "**`!slot <mise>`** : Machine à sous.\n"
        "> 🔥 **Bonus :** Gagne 7 fois de suite pour obtenir le rôle **Hakari**.\n"
        "**`!dice <mise>`** : Duel de dés contre le bot.\n"
        "**`!roulette <mise> <couleur>`** : Rouge/Noir/Vert (x2 ou x14).\n"
        "**`!blackjack <mise>`** : Le jeu du 21."
    ), inline=False)

    embed.add_field(name="🏇 __Multijoueur & Paris__", value=(
        "**`!race`** : Lancer une course de chevaux (30s pour parier).\n"
        "**`!bet <mise> <cheval>`** : Parier sur un cheval (1-5).\n"
        "> 🏅 **Bonus :** 10 victoires cumulées = rôle **Hockey Genius**.\n"
        "**`!morpion @user <mise>`** : Défier quelqu'un au Tic-Tac-Toe."
    ), inline=False)

    embed.add_field(name="🛒 __Boutique & Admin__", value=(
        "**`!shop`** : Voir les prix des rôles.\n"
        "**`!buy <item>`** : Acheter un rôle (ex: `!buy juif`).\n"
        "**`!admingive`** : (Admin) Créer de l'argent."
    ), inline=False)

    embed.set_footer(text="Pandora Casino - Taux de victoire boosté à 70% !")
    await ctx.send(embed=embed)

# --- 6. ÉCONOMIE ---
@bot.command(aliases=["top", "rich"])
async def leaderboard(ctx):
    db = load_db()
    users = [(k, v) for k, v in db.items() if k.isdigit() and isinstance(v, (int, float))]
    users.sort(key=lambda x: x[1], reverse=True)
    desc = ""
    for idx, (uid, bal) in enumerate(users[:10], 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        desc += f"**{medal} <@{uid}>** : {int(bal):,} coins\n"
    await ctx.send(embed=discord.Embed(title="🏆 CLASSEMENT", description=desc if desc else "Vide", color=COL_GOLD))

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    db = load_db()
    bal = db.get(str(target.id), 0)
    await ctx.send(embed=discord.Embed(description=f"💰 **{target.display_name}** a **{int(bal):,} coins**", color=COL_BLUE))

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user) # 10 minutes
async def work(ctx):
    db = load_db()
    gain = random.randint(200, 800)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"🔨 Tu as travaillé et gagné **{gain} coins**.", color=COL_GREEN))

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_daily"
    if time.time() - db.get(key, 0) < 86400: # 24h
        return await ctx.send(embed=discord.Embed(description="⏳ Reviens demain !", color=COL_RED))
    
    gain = random.randint(1000, 3000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"🎁 **{gain} coins** ajoutés !", color=COL_GOLD))

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member == ctx.author: return
    db = load_db()
    uid, tid = str(ctx.author.id), str(member.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0 or db.get(uid, 0) < amount:
        return await ctx.send("❌ Pas assez d'argent.")
    
    # SYSTEME DE TAXE
    tax = int(amount * TAX_RATE)
    final = amount - tax
    
    db[uid] -= amount
    db[tid] = db.get(tid, 0) + final
    save_db(db)
    
    embed = discord.Embed(title="💸 Transfert", color=COL_GREEN)
    embed.add_field(name="Montant", value=str(amount))
    embed.add_field(name="Taxe (5%)", value=f"-{tax}")
    embed.add_field(name="Reçu", value=f"**{final}**")
    embed.set_footer(text=f"Envoyé à {member.display_name}")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db()
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db)
    await ctx.send(f"✅ **{amount}** donnés administrativement à {member.mention}.")

# --- MODIFICATION ICI : ROB ---
@bot.command()
@commands.cooldown(1, 1200, commands.BucketType.user) # 20 MINUTES (1200 secondes)
async def rob(ctx, member: discord.Member):
    # VERIFICATION ROLE "Juif" (Insensible à la casse)
    user_roles = [r.name.lower() for r in ctx.author.roles]
    if "juif" not in user_roles:
        # Reset le cooldown si le joueur n'a pas le rôle pour pas qu'il attende pour rien
        ctx.command.reset_cooldown(ctx)
        return await ctx.send(embed=discord.Embed(description="⛔ Tu dois acheter le rôle **Juif** au `!shop` pour voler !", color=COL_RED))

    if member.bot or member == ctx.author: return
    db = load_db()
    vic_bal = db.get(str(member.id), 0)
    
    if vic_bal < 500: return await ctx.send("❌ Il est trop pauvre.")
    
    # 50% de chance de réussir le vol
    if random.random() < 0.5:
        stolen = int(vic_bal * random.uniform(0.05, 0.2)) # Vole entre 5% et 20%
        db[str(ctx.author.id)] += stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"🥷 Tu as volé **{stolen} coins** à {member.display_name} !", color=COL_GREEN))
    else:
        fine = 500
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"👮 Tu t'es fait attraper ! Amende de **{fine} coins**.", color=COL_RED))

# --- 7. JEUX (DICE, SLOT, ROULETTE - 70% WIN) ---

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")

    # TRUCAGE 70%
    if random.random() < 0.70:
        p_score = random.randint(7, 12) # Score haut
        b_score = random.randint(2, p_score - 1) # Score plus bas
        win = True
    else:
        b_score = random.randint(7, 12)
        p_score = random.randint(2, b_score - 1)
        win = False

    embed = discord.Embed(title="🎲 Dés", color=COL_GREEN if win else COL_RED)
    embed.add_field(name="Toi", value=f"🎲 {p_score}")
    embed.add_field(name="Bot", value=f"🎲 {b_score}")

    if win:
        db[uid] += amount
        embed.description = f"🎉 **Gagné !** +{amount} coins"
    else:
        db[uid] -= amount
        embed.description = f"❌ **Perdu...** -{amount} coins"
    
    save_db(db)
    await ctx.send(embed=embed)

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")

    symbols = ["🍒", "7️⃣", "💎", "🍇", "🔔"]
    
    # TRUCAGE 70%
    if random.random() < 0.70:
        s = random.choice(symbols)
        res = [s, s, s] # Force 3 pareils
        mult = 100 if s == "7️⃣" else 20
    else:
        res = random.sample(symbols, 3) # Force différents (ou presque)
        if res[0] == res[1] or res[1] == res[2]: mult = 1.5 # Petite chance quand même
        else: mult = 0

    embed = discord.Embed(title="🎰 Slots", description=f"🔹 {' | '.join(res)} 🔹", color=COL_BLUE)
    streak_key = f"{uid}_slot_streak"

    if mult > 0:
        profit = int(amount * mult)
        db[uid] += (profit - amount) # Gain net
        embed.color = COL_GREEN
        embed.add_field(name="JACKPOT !", value=f"Tu gagnes **{profit} coins** !")
        
        # HAKARI (7 wins d'affilée)
        db[streak_key] = db.get(streak_key, 0) + 1
        if db[streak_key] >= 7:
            role = discord.utils.get(ctx.guild.roles, name="Hakari")
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                embed.add_field(name="🔥 HAKARI DANCE", value="7 victoires de suite ! Rôle **Hakari** obtenu !", inline=False)
    else:
        db[uid] -= amount
        db[streak_key] = 0 # Reset streak
        embed.color = COL_RED
        embed.set_footer(text="Perdu...")

    save_db(db)
    await ctx.send(embed=embed)

@bot.command()
async def roulette(ctx, amount_str: str, choice: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")

    choice = choice.lower()
    valid = ["rouge", "noir", "vert", "red", "black", "green"]
    
    # TRUCAGE 70%
    force_win = random.random() < 0.70
    
    num = random.randint(0, 36)
    color = "vert" if num == 0 else ("rouge" if num % 2 == 1 else "noir")

    # Si on doit gagner, on change le résultat pour qu'il corresponde au choix
    if force_win:
        if choice in ["rouge", "red"]: color = "rouge"; num = 1
        elif choice in ["noir", "black"]: color = "noir"; num = 2
        elif choice in ["vert", "green"]: color = "vert"; num = 0
        elif choice.isdigit(): num = int(choice); color = "vert" if num==0 else ("rouge" if num%2==1 else "noir")

    # Vérification classique
    win = False
    mult = 0
    if choice in ["rouge", "red"] and color == "rouge": win=True; mult=2
    elif choice in ["noir", "black"] and color == "noir": win=True; mult=2
    elif choice in ["vert", "green"] and color == "vert": win=True; mult=14
    elif choice.isdigit() and int(choice) == num: win=True; mult=36

    embed = discord.Embed(title="🎡 Roulette", description=f"Boule : **{num} ({color.upper()})**", color=COL_BLUE)
    
    if win:
        profit = amount * mult
        db[uid] += (profit - amount)
        embed.color = COL_GREEN
        embed.add_field(name="GAGNÉ !", value=f"+{profit} coins")
    else:
        db[uid] -= amount
        embed.color = COL_RED
        embed.add_field(name="PERDU", value=f"-{amount} coins")
    
    save_db(db)
    await ctx.send(embed=embed)

# --- 8. MORPION (DUEL PVP) ---
class MorpionButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="‎", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("Pas ton tour !", ephemeral=True)
        if view.board[self.y][self.x] != 0: return

        val = 1 if view.current_player == view.p1 else 2
        view.board[self.y][self.x] = val
        self.style = discord.ButtonStyle.danger if val == 1 else discord.ButtonStyle.success
        self.label = "X" if val == 1 else "O"
        self.disabled = True
        
        winner = view.check_winner()
        if winner:
            view.stop()
            w_user = view.p1 if winner == 1 else view.p2
            if view.mise > 0:
                db = load_db()
                db[str(w_user.id)] += view.mise * 2
                save_db(db)
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{w_user.display_name}** gagne {view.mise*2} coins !", view=view)
        elif all(c != 0 for row in view.board for c in row):
            view.stop()
            if view.mise > 0:
                db = load_db()
                db[str(view.p1.id)] += view.mise
                db[str(view.p2.id)] += view.mise
                save_db(db)
            await interaction.response.edit_message(content="🤝 Match nul (Remboursé).", view=view)
        else:
            view.current_player = view.p2 if view.current_player == view.p1 else view.p1
            await interaction.response.edit_message(content=f"Au tour de {view.current_player.mention}", view=view)

class MorpionView(discord.ui.View):
    def __init__(self, p1, p2, mise):
        super().__init__(timeout=60)
        self.p1, self.p2, self.mise = p1, p2, mise
        self.current_player = p1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for y in range(3):
            for x in range(3): self.add_item(MorpionButton(x, y))
    
    def check_winner(self):
        b = self.board
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != 0: return b[i][0]
            if b[0][i] == b[1][i] == b[2][i] != 0: return b[0][i]
        if b[0][0] == b[1][1] == b[2][2] != 0: return b[0][0]
        if b[0][2] == b[1][1] == b[2][0] != 0: return b[0][2]
        return None

@bot.command()
async def morpion(ctx, opponent: discord.Member, amount_str: str="0"):
    if opponent.bot or opponent == ctx.author: return
    db = load_db()
    try: mise = int(amount_str)
    except: mise = 0
    
    if mise > 0:
        if db.get(str(ctx.author.id),0) < mise: return await ctx.send("Pas assez d'argent.")
        if db.get(str(opponent.id),0) < mise: return await ctx.send("L'adversaire n'a pas assez.")

    view = discord.ui.View()
    btn = discord.ui.Button(label="Accepter Duel", style=discord.ButtonStyle.success)
    async def cb(interaction):
        if interaction.user != opponent: return
        if mise > 0:
            db[str(ctx.author.id)] -= mise
            db[str(opponent.id)] -= mise
            save_db(db)
        await interaction.response.edit_message(content=f"⚔️ **Morpion** : {ctx.author.mention} vs {opponent.mention} ({mise} coins)", view=MorpionView(ctx.author, opponent, mise))
    btn.callback = cb
    view.add_item(btn)
    await ctx.send(f"{opponent.mention}, duel de Morpion pour {mise} coins ?", view=view)

# --- 9. BLACKJACK ---
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=60)
        self.author_id, self.amount, self.db = author_id, amount, db
        self.deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
        self.player = [self.draw(), self.draw()]
        self.dealer = [self.draw(), self.draw()]
    
    def draw(self): return random.choice(self.deck)
    def calc(self, h):
        s = sum(h); a = h.count(11)
        while s > 21 and a: s-=10; a-=1
        return s
    
    async def update(self, interaction, end=False, msg=""):
        e = discord.Embed(title="🃏 Blackjack", color=COL_BLUE)
        e.add_field(name=f"Toi ({self.calc(self.player)})", value=str(self.player))
        if end:
            e.add_field(name=f"Croupier ({self.calc(self.dealer)})", value=str(self.dealer))
            e.description = msg
            e.color = COL_GREEN if "Gagné" in msg else (COL_RED if "Perdu" in msg else COL_GOLD)
            for c in self.children: c.disabled = True
            self.stop()
        else:
            e.add_field(name="Croupier", value=f"[{self.dealer[0]}, ?]")
        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, i, b):
        if i.user.id != self.author_id: return
        self.player.append(self.draw())
        if self.calc(self.player) > 21: await self.update(i, True, "💥 Sauté ! Perdu.")
        else: await self.update(i)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, i, b):
        if i.user.id != self.author_id: return
        while self.calc(self.dealer) < 17: self.dealer.append(self.draw())
        p, d = self.calc(self.player), self.calc(self.dealer)
        uid = str(self.author_id)
        if d > 21 or p > d:
            self.db[uid] += self.amount * 2
            save_db(self.db)
            await self.update(i, True, "🎉 Gagné !")
        elif p == d:
            self.db[uid] += self.amount
            save_db(self.db)
            await self.update(i, True, "🤝 Égalité.")
        else:
            save_db(self.db)
            await self.update(i, True, "❌ Perdu.")

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    db[uid] -= amount
    save_db(db)
    await ctx.send(embed=discord.Embed(title="🃏 Blackjack", color=COL_BLUE), view=BlackjackView(ctx.author.id, amount, db))

# --- 10. COURSE (RACE) ---
race_open = False
race_bets = []

@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return await ctx.send("⚠️ Course en cours.")
    race_open = True; race_bets = []
    
    await ctx.send("🏇 **Début des paris !** Tape `!bet <mise> <cheval 1-5>`. (20s)")
    await asyncio.sleep(20)
    
    if not race_bets:
        race_open = False; return await ctx.send("❌ Course annulée (0 pari).")
    
    msg = await ctx.send("🏁 **C'EST PARTI !**")
    track = ["🐎", "🦄", "🦓", "🐖", "🐆"]
    for _ in range(3):
        await asyncio.sleep(1.5)
        random.shuffle(track)
        await msg.edit(content="\n".join([f"{i+1}. {t} 💨" for i, t in enumerate(track)]))
        
    winner = random.randint(1, 5)
    db = load_db()
    res = f"👑 **Le Cheval #{winner} gagne !**\n"
    
    for b in race_bets:
        if b['horse'] == winner:
            gain = b['amount'] * 3
            db[str(b['uid'])] = db.get(str(b['uid']), 0) + gain
            res += f"✅ <@{b['uid']}> gagne {gain} coins !\n"
            
            # HOCKEY GENIUS (10 wins cumulées)
            k = f"{b['uid']}_race_wins"
            db[k] = db.get(k, 0) + 1
            if db[k] == 10:
                r = discord.utils.get(ctx.guild.roles, name="Hockey Genius")
                u = ctx.guild.get_member(b['uid'])
                if r and u: await u.add_roles(r); res += "🏆 **ROLE HOCKEY GENIUS OBTENU !**\n"
                
    save_db(db); race_open = False
    await ctx.send(embed=discord.Embed(description=res, color=COL_GOLD))

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    if not race_open: return await ctx.send("❌ Pas de course.")
    if not (1 <= horse <= 5): return await ctx.send("❌ Cheval 1-5.")
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    
    db[uid] -= amount; save_db(db)
    race_bets.append({'uid': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"🎟️ Pari de {amount} sur #{horse}.")

# --- 11. BOUTIQUE ---
@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 BOUTIQUE", color=COL_BLUE)
    for k, v in SHOP_ITEMS.items(): e.add_field(name=k.upper(), value=f"💰 {v:,} coins", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    if item not in SHOP_ITEMS: return await ctx.send("❌ Article inconnu.")
    db = load_db(); uid = str(ctx.author.id)
    price = SHOP_ITEMS[item]
    
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    role = discord.utils.get(ctx.guild.roles, name=item) # Nom du rôle
    if not role: return await ctx.send(f"❌ Rôle '{item}' introuvable sur le serveur.")
    
    await ctx.author.add_roles(role)
    db[uid] -= price; save_db(db)
    await ctx.send(f"✅ Tu as acheté **{item}** !")

# --- 12. ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Attends encore {int(error.retry_after)}s.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission.")
    else: print(error)

# LANCEMENT
keep_alive()
try: bot.run(os.environ.get('TOKEN'))
except: pass
