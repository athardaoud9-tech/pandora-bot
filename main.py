import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread
import logging

# --- 1. CONFIGURATION DU SERVEUR WEB (FIX RENDER) ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "Pandora Casino est en ligne (vFinal - Animé & Équilibré) !"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# --- 2. CONFIGURATION BOT ET BDD ---
DB_FILE = "database.json"
TAX_RATE = 0.05 

COL_GOLD = 0xFFD700
COL_RED = 0xE74C3C
COL_GREEN = 0x2ECC71
COL_BLUE = 0x3498DB
COL_DARK = 0x2C3E50

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914

# 🛒 BOUTIQUE (PRIX ÉQUILIBRÉS)
SHOP_ITEMS = {
    "juif": 100000,         # 100k (Accessible)
    "riche": 5000000,       # 5M (Difficile)
    "roi": 50000000         # 50M (Objectif ultime)
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

# --- 4. ÉVÉNEMENTS ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name="!helpme | Casino V2"))

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

# --- 5. HELPME ---
@bot.command()
async def helpme(ctx):
    embed = discord.Embed(
        title="✨ PANDORA CASINO - AIDE ✨", 
        description="Voici la liste complète des commandes disponibles pour t'enrichir (ou tout perdre) !", 
        color=COL_GOLD
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else "")
    embed.add_field(name="💰 ÉCONOMIE", value="`!bal` : Voir ton solde\n`!work` : Travailler (toutes les 10m)\n`!daily` : Cadeau quotidien\n`!leaderboard` : Top 10 des riches\n`!give @user <montant>` : Donner de l'argent", inline=False)
    embed.add_field(name="🎰 JEUX DE HASARD", value="`!slot <mise>` : Machine à sous\n`!dice <mise>` : Duel de dés\n`!roulette <mise> <choix>` : Roulette", inline=False)
    embed.add_field(name="🃏 STRATÉGIE & DEFIS", value="`!blackjack <mise>` : Atteins 21 sans sauter\n`!morpion @user <mise>` : Duel tactique", inline=False)
    embed.add_field(name="🏇 PARIS HIPPIQUES", value="`!race` : Lance une course\n`!bet <mise> <n°>` : Parie sur ton favori", inline=False)
    embed.add_field(name="🛒 BOUTIQUE & CRIME", value="`!shop` : Rôles à acheter\n`!buy <nom>` : Acheter un rôle\n`!rob @user` : Voler (Rôle Juif requis)", inline=False)
    embed.set_footer(text="Pandora Casino • Utilise le préfixe '!' avant chaque commande", icon_url=ctx.guild.icon.url if ctx.guild.icon else "")
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
    gain = random.randint(300, 1000)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"🔨 Tu as travaillé et gagné **{gain} coins**.", color=COL_GREEN))

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_daily"
    if time.time() - db.get(key, 0) < 86400:
        return await ctx.send(embed=discord.Embed(description="⏳ Reviens demain !", color=COL_RED))
    
    gain = random.randint(2000, 5000)
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
    
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    tax = int(amount * TAX_RATE)
    final = amount - tax
    
    db[uid] -= amount
    db[tid] = db.get(tid, 0) + final
    save_db(db)
    await ctx.send(embed=discord.Embed(description=f"💸 **Envoi :** {amount}\n🏛️ **Taxe (5%) :** -{tax}\n✅ **Reçu :** {final}", color=COL_GREEN))

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db()
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db)
    await ctx.send(f"✅ **{amount:,} coins** donnés à {member.mention}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def admintake(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    current = db.get(uid, 0)
    new_bal = max(0, current - amount)
    db[uid] = new_bal
    save_db(db)
    await ctx.send(f"📉 **{amount:,} coins** retirés à {member.mention}. (Nouveau solde: {new_bal:,})")

@bot.command()
@commands.cooldown(1, 1200, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    user_roles = [r.name.lower() for r in ctx.author.roles]
    if "juif" not in user_roles:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send(embed=discord.Embed(description="⛔ Rôle **Juif** requis (Boutique) !", color=COL_RED))

    if member.bot or member == ctx.author: return
    db = load_db()
    vic_bal = db.get(str(member.id), 0)
    
    if vic_bal < 1000: return await ctx.send("❌ Il est trop pauvre (moins de 1000).")
    
    if random.random() < 0.45:
        stolen = int(vic_bal * random.uniform(0.05, 0.15))
        db[str(ctx.author.id)] += stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"🥷 Tu as volé **{stolen} coins** !", color=COL_GREEN))
    else:
        fine = 1000
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"👮 Attrapé ! Amende de **{fine} coins**.", color=COL_RED))

# --- 7. JEUX AVEC ANIMATIONS ET ODDS RÉALISTES ---

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent !")

    anim_embed = discord.Embed(title="🎲 Lancer de dés...", color=COL_GOLD)
    anim_embed.set_image(url="https://media.tenor.com/DOX2z6kZl84AAAAi/dice-roll.gif")
    msg = await ctx.send(embed=anim_embed)
    await asyncio.sleep(2.5)

    p_score = random.randint(1, 6)
    b_score = random.randint(1, 6)
    win = p_score > b_score

    embed = discord.Embed(title="🎲 Résultat des Dés", color=COL_GREEN if win else COL_RED)
    embed.add_field(name="Toi", value=f"**{p_score}**")
    embed.add_field(name="Croupier", value=f"**{b_score}**")

    if win:
        db[uid] += amount
        embed.description = f"🎉 **GAGNÉ !** Tu remportes **{amount*2} coins**"
    else:
        db[uid] -= amount
        embed.description = f"❌ **PERDU.** Tu perds **{amount} coins**"
        if p_score == b_score: embed.set_footer(text="Égalité : L'avantage est à la banque.")
    
    save_db(db)
    await msg.edit(embed=embed)

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent !")

    anim_embed = discord.Embed(title="🎰 Machine à sous...", description="Les rouleaux tournent...", color=COL_GOLD)
    anim_embed.set_image(url="https://media.tenor.com/0vKz5tJ3gBQAAAAi/slot-machine-slots.gif")
    msg = await ctx.send(embed=anim_embed)
    await asyncio.sleep(3)

    user_roles = [r.name.lower() for r in ctx.author.roles]
    win_rate = 0.45 if "hakari" in user_roles else 0.30

    symbols = ["🍒", "💎", "🍇", "🔔", "🍊"]
    
    if random.random() < win_rate:
        luck = random.random()
        if luck < 0.001:
            res = ["7️⃣", "7️⃣", "7️⃣"]
            mult = 1000
        elif luck < 0.05:
            s = random.choice(symbols)
            res = [s, s, s]
            mult = 10
        else:
            s = random.choice(symbols)
            res = [s, s, random.choice([x for x in symbols if x != s])]
            random.shuffle(res)
            mult = 2
    else:
        res = random.sample(symbols, 3)
        mult = 0

    embed = discord.Embed(title="🎰 Machine à sous", description=f"🟩 **[ {' | '.join(res)} ]** 🟩", color=COL_BLUE)
    streak_key = f"{uid}_slot_streak"

    if mult > 0:
        profit = int(amount * mult)
        db[uid] += (profit - amount)
        embed.color = COL_GREEN
        embed.add_field(name="RÉSULTAT", value=f"🎉 **JACKPOT !** Tu gagnes **{profit:,} coins** (x{mult})")
        
        # HAKARI (5 fois d'affilée minimum)
        db[streak_key] = db.get(streak_key, 0) + 1
        if db[streak_key] >= 5:
            role = discord.utils.get(ctx.guild.roles, name="Hakari")
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                embed.add_field(name="🔥 HAKARI", value="Rôle débloqué !", inline=False)
    else:
        db[uid] -= amount
        db[streak_key] = 0 # Retour à 0 si on perd (pour forcer 5x d'affilée)
        embed.color = COL_RED
        embed.add_field(name="RÉSULTAT", value=f"❌ **PERDU.** (-{amount:,} coins)")

    save_db(db)
    await msg.edit(embed=embed)

@bot.command()
async def roulette(ctx, amount_str: str, choice: str):
    db = load_db()
    uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent !")

    choice = choice.lower()
    if choice not in ["rouge", "noir", "vert", "red", "black", "green"] and not choice.isdigit():
        return await ctx.send("❌ Choix invalide (rouge, noir, vert, ou 0-36).")

    anim_embed = discord.Embed(title="🎡 Roulette...", description="La bille tourne...", color=COL_GOLD)
    anim_embed.set_image(url="https://media.tenor.com/7bEw9q_h7CMAAAAi/roulette-casino.gif")
    msg = await ctx.send(embed=anim_embed)
    await asyncio.sleep(4)

    num = random.randint(0, 36)
    if num == 0: color = "vert"
    elif num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]: color = "rouge"
    else: color = "noir"

    win = False
    mult = 0
    if choice in ["rouge", "red"] and color == "rouge": win = True; mult = 2
    elif choice in ["noir", "black"] and color == "noir": win = True; mult = 2
    elif choice in ["vert", "green"] and color == "vert": win = True; mult = 14
    elif choice.isdigit() and int(choice) == num: win = True; mult = 36

    embed = discord.Embed(title="🎡 Roulette", description=f"Résultat : **{num} ({color.upper()})**", color=COL_BLUE)
    
    if win:
        profit = amount * mult
        db[uid] += (profit - amount)
        embed.color = COL_GREEN
        embed.add_field(name="RÉSULTAT", value=f"🎉 **GAGNÉ !** Tu remportes **{profit:,}**")
    else:
        db[uid] -= amount
        embed.color = COL_RED
        embed.add_field(name="RÉSULTAT", value=f"❌ **PERDU.** Tu perds **{amount:,}**")
    
    save_db(db)
    await msg.edit(embed=embed)

# --- 8. MORPION (Intact) ---
class MorpionButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="‎", row=y)
        self.x, self.y = x, y

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
                db[str(w_user.id)] = db.get(str(w_user.id), 0) + view.mise * 2
                save_db(db)
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{w_user.display_name}** gagne {view.mise*2} coins !", view=view)
        elif all(c != 0 for row in view.board for c in row):
            view.stop()
            if view.mise > 0:
                db = load_db()
                db[str(view.p1.id)] = db.get(str(view.p1.id), 0) + view.mise
                db[str(view.p2.id)] = db.get(str(view.p2.id), 0) + view.mise
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
        if db.get(str(ctx.author.id),0) < mise: return await ctx.send("Tu n'as pas assez d'argent.")
        if db.get(str(opponent.id),0) < mise: return await ctx.send("L'adversaire n'a pas assez.")

    view = discord.ui.View()
    btn = discord.ui.Button(label="Accepter Duel", style=discord.ButtonStyle.success)
    async def cb(interaction):
        if interaction.user != opponent: return
        if mise > 0:
            curr_db = load_db()
            if curr_db.get(str(ctx.author.id),0) < mise or curr_db.get(str(opponent.id),0) < mise:
                return await interaction.response.send_message("❌ Fonds insuffisants.", ephemeral=True)
            curr_db[str(ctx.author.id)] -= mise
            curr_db[str(opponent.id)] -= mise
            save_db(curr_db)
        await interaction.response.edit_message(content=f"⚔️ **Morpion** : {ctx.author.mention} vs {opponent.mention} ({mise} coins)", view=MorpionView(ctx.author, opponent, mise))
    btn.callback = cb
    view.add_item(btn)
    await ctx.send(f"{opponent.mention}, duel de Morpion pour {mise} coins ?", view=view)

# --- 9. BLACKJACK (Corrigé) ---
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount):
        super().__init__(timeout=60)
        self.author_id, self.amount = author_id, amount
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
        
        db = load_db()
        uid = str(self.author_id)
        
        if d > 21 or p > d:
            db[uid] = db.get(uid, 0) + self.amount * 2
            save_db(db)
            await self.update(i, True, "🎉 Gagné !")
        elif p == d:
            db[uid] = db.get(uid, 0) + self.amount
            save_db(db)
            await self.update(i, True, "🤝 Égalité.")
        else:
            await self.update(i, True, "❌ Perdu.")

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")
    
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent !")
    
    db[uid] -= amount
    save_db(db)
    
    # FIX : On affiche la main dès le lancement de la commande
    view = BlackjackView(ctx.author.id, amount)
    e = discord.Embed(title="🃏 Blackjack", color=COL_BLUE)
    e.add_field(name=f"Toi ({view.calc(view.player)})", value=str(view.player))
    e.add_field(name="Croupier", value=f"[{view.dealer[0]}, ?]")
    
    await ctx.send(embed=e, view=view)

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
    for _ in range(4):
        await asyncio.sleep(1.5)
        random.shuffle(track)
        await msg.edit(content="\n".join([f"{i+1}. {t} {'💨' * random.randint(1,3)}" for i, t in enumerate(track)]))
        
    winner = random.randint(1, 5)
    db = load_db()
    res = f"👑 **Le Cheval #{winner} gagne !**\n"
    
    for b in race_bets:
        if b['horse'] == winner:
            gain = b['amount'] * 4
            db[str(b['uid'])] = db.get(str(b['uid']), 0) + gain
            res += f"✅ <@{b['uid']}> gagne {gain:,} coins !\n"
            
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
    
    if db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent !")
    
    db[uid] -= amount; save_db(db)
    race_bets.append({'uid': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"🎟️ Pari de {amount:,} coins sur le cheval #{horse}.")

# --- 11. BOUTIQUE ---
@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 BOUTIQUE DU CASINO", color=COL_BLUE)
    e.description = "Achète des rôles pour prouver ta richesse ou débloquer des commandes !"
    for k, v in SHOP_ITEMS.items(): e.add_field(name=f"👑 Rôle {k.capitalize()}", value=f"💰 **{v:,} coins**", inline=False)
    e.set_footer(text="Tape !buy <nom_du_role>")
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    if item not in SHOP_ITEMS: return await ctx.send("❌ Article inconnu.")
    db = load_db(); uid = str(ctx.author.id)
    price = SHOP_ITEMS[item]
    
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    role = discord.utils.get(ctx.guild.roles, name=item)
    if not role: return await ctx.send(f"❌ Rôle '{item}' introuvable sur le serveur Discord.")
    
    await ctx.author.add_roles(role)
    db[uid] -= price; save_db(db)
    await ctx.send(f"✅ Transaction réussie ! Tu es maintenant **{item.capitalize()}** !")

# --- 12. ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Attends encore {int(error.retry_after)} secondes.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")
    else: print(error)


# --- DÉMARRAGE RENDER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=port, use_reloader=False))
    web_thread.daemon = True
    web_thread.start()
    print(f"🚀 Serveur Web activé sur le port {port}")

    time.sleep(5)

    token = os.environ.get('TOKEN')
    if token:
        try:
            print("🤖 Tentative de connexion à Discord...")
            bot.run(token)
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
    else:
        print("❌ Erreur : TOKEN introuvable.")
