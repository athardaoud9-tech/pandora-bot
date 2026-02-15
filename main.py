import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR REPLIT/HOSTING) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino V4 est en ligne !"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES & UTILITAIRES ---
DB_FILE = "database.json"
TAX_RATE = 0.05 # 5% de taxe sur les échanges (!give)

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

# CONFIGURATION JEUX & SALONS
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914
SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 20, 15, 8, 2] 

race_open = False
race_bets = [] 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora V4 est prêt !")

# --- 4. CLASSES D'INTERFACE (VIEWS) ---

# --- NOUVEAU JEU : HIGH / LOW ---
class HighLowView(discord.ui.View):
    def __init__(self, author, amount, db):
        super().__init__(timeout=60)
        self.author = author
        self.amount = amount
        self.db = db
        self.current_number = random.randint(1, 100)
        self.embed = None # Sera défini après l'envoi

    def get_embed(self, status="En attente...", color=0x4b41e6):
        emb = discord.Embed(title="📈 High or Low ?", description=f"Mise : **{self.amount} coins**", color=color)
        emb.add_field(name="Nombre Actuel", value=f"# **{self.current_number}**", inline=False)
        emb.add_field(name="Ton choix", value="Le prochain nombre sera-t-il plus **grand** ou plus **petit** ?", inline=False)
        emb.set_footer(text=status)
        return emb

    async def end_game(self, interaction, won, next_num):
        uid = str(self.author.id)
        for child in self.children: child.disabled = True
        
        if won:
            gain = self.amount * 2
            self.db[uid] = self.db.get(uid, 0) + gain
            color = 0x00ff00
            msg = f"🎉 GAGNÉ ! Le nombre était **{next_num}**. Tu gagnes +{gain - self.amount} coins."
        else:
            # L'argent est déjà retiré au lancement, on ne fait rien
            color = 0xff0000
            msg = f"❌ PERDU... Le nombre était **{next_num}**."
        
        save_db(self.db)
        emb = discord.Embed(title="📈 High or Low - Fin", description=msg, color=color)
        emb.add_field(name="Nombre de départ", value=str(self.current_number))
        emb.add_field(name="Nombre d'arrivée", value=str(next_num))
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Plus Grand (High)", style=discord.ButtonStyle.success, emoji="⬆️")
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author: return
        next_num = random.randint(1, 100)
        if next_num == self.current_number: next_num += 1 # Pas d'égalité parfaite
        await self.end_game(interaction, next_num > self.current_number, next_num)

    @discord.ui.button(label="Plus Petit (Low)", style=discord.ButtonStyle.danger, emoji="⬇️")
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author: return
        next_num = random.randint(1, 100)
        if next_num == self.current_number: next_num -= 1
        await self.end_game(interaction, next_num < self.current_number, next_num)

# --- NOUVELLE INTERFACE DICE ---
class DiceView(discord.ui.View):
    def __init__(self, author, amount, db):
        super().__init__(timeout=60)
        self.author = author
        self.amount = amount
        self.db = db

    @discord.ui.button(label="🎲 Lancer les dés", style=discord.ButtonStyle.primary)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author: return
        
        player_roll = [random.randint(1, 6), random.randint(1, 6)]
        bot_roll = [random.randint(1, 6), random.randint(1, 6)]
        p_sum = sum(player_roll)
        b_sum = sum(bot_roll)
        uid = str(self.author.id)

        embed = discord.Embed(title="🎲 Duel de Dés", color=0x4b41e6)
        embed.add_field(name=f"Toi ({p_sum})", value=f"{player_roll[0]} + {player_roll[1]}", inline=True)
        embed.add_field(name=f"Bot ({b_sum})", value=f"{bot_roll[0]} + {bot_roll[1]}", inline=True)

        if p_sum > b_sum:
            gain = self.amount * 2
            self.db[uid] = self.db.get(uid, 0) + gain
            embed.color = 0x00ff00
            embed.description = f"🎉 **Tu gagnes !** +{gain - self.amount} coins net."
        elif p_sum < b_sum:
            embed.color = 0xff0000
            embed.description = f"❌ **Le Bot gagne.** Tu perds ta mise."
        else:
            self.db[uid] = self.db.get(uid, 0) + self.amount # Remboursement
            embed.description = "🤝 **Égalité !** Mise remboursée."
        
        save_db(self.db)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

# --- 5. COMMANDES DE JEUX ---

@bot.command(aliases=["hl", "plusoumoins"])
async def hilo(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")

    # On retire la mise tout de suite
    db[uid] -= amount
    save_db(db)

    view = HighLowView(ctx.author, amount, db)
    await ctx.send(embed=view.get_embed(), view=view)

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")

    db[uid] -= amount
    save_db(db)
    
    view = DiceView(ctx.author, amount, db)
    embed = discord.Embed(title="🎲 Duel de Dés", description=f"Mise : **{amount} coins**\nClique ci-dessous pour lancer !", color=0x4b41e6)
    await ctx.send(embed=embed, view=view)

# --- 6. SYSTÈME ÉCONOMIE & TAXES ---

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_last_daily"
    # Cooldown de 12h pour le daily
    if time.time() - db.get(key, 0) < 43200: 
        return await ctx.send("⏳ Reviens plus tard pour ton daily.")
    
    # REWARD ALEATOIRE 1000 - 5000
    gain = random.randint(1000, 5000)
    
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(f"🎁 **Daily !** Tu as reçu **{gain} coins** aujourd'hui !")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user) # 600 secondes = 10 minutes
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 350)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(f"🔨 Tu as travaillé dur et gagné **{gain} coins** !")

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member.id == ctx.author.id: return await ctx.send("❌ Impossible.")
    
    db = load_db()
    u_send = str(ctx.author.id)
    u_recv = str(member.id)
    
    amount = parse_amount(amount_str, db.get(u_send, 0))
    if amount <= 0 or db.get(u_send, 0) < amount: return await ctx.send("❌ Fonds insuffisants.")

    # CALCUL TAXE
    tax_amount = int(amount * TAX_RATE)
    final_amount = amount - tax_amount

    db[u_send] -= amount
    db[u_recv] = db.get(u_recv, 0) + final_amount
    save_db(db)
    
    await ctx.send(f"💸 **{ctx.author.display_name}** envoie {amount} coins à {member.mention}.\n📉 **Taxe (5%)** : -{tax_amount} coins.\n✅ **Reçu** : {final_amount} coins.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount_str: str):
    """Commande Admin pour retirer de l'argent (Impôts/Amende)"""
    db = load_db()
    uid = str(member.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0: return await ctx.send("❌ Montant invalide.")
    
    db[uid] = max(0, db.get(uid, 0) - amount)
    save_db(db)
    await ctx.send(f"👮 **IMPÔTS :** L'État (Admin) a prélevé **{amount} coins** à {member.mention}.")

@bot.command(aliases=["admingive"])
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"👑 **ADMIN GIVE:** +{amount} pour {member.mention}.")

# --- 7. RESTE DES COMMANDES (Course, Slot, Morpion...) ---
# (J'ai gardé ton code existant pour Race, Slot, etc. et je l'intègre ici)

@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return await ctx.send("🏇 Course déjà en cours !")
    race_open = True; race_bets = []
    
    await ctx.send("🏇 **Course ouverte !** `!bet <mise> <cheval 1-5>` (30s)")
    await asyncio.sleep(30)
    
    if not race_bets: race_open = False; return await ctx.send("❌ Course annulée (0 paris).")
    
    msg = await ctx.send("🚫 **Paris fermés !** Départ..."); await asyncio.sleep(1)
    await msg.edit(content="🏇 🏇 🏇 ..."); await asyncio.sleep(2)
    
    winner = random.randint(1, 5)
    db = load_db(); winners_txt = []
    
    for b in race_bets:
        if b['horse'] == winner:
            gain = b['amount'] * 2
            db[str(b['user'])] = db.get(str(b['user']), 0) + gain
            
            # Check Role Dompteur
            w_key = f"{b['user']}_race_wins"
            db[w_key] = db.get(w_key, 0) + 1
            if db[w_key] >= 10:
                mem = ctx.guild.get_member(b['user'])
                r = discord.utils.get(ctx.guild.roles, name="Dompteur de chevaux")
                if mem and r: await mem.add_roles(r)
            
            winners_txt.append(f"<@{b['user']}> (+{gain})")

    save_db(db); race_open = False; race_bets = []
    res = ", ".join(winners_txt) if winners_txt else "Personne !"
    await ctx.send(f"🏁 Le cheval **#{winner}** gagne ! Bravo : {res}")

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_open, race_bets
    if not race_open: return
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return
    
    for b in race_bets:
        if b['user'] == ctx.author.id: return await ctx.send("❌ Déjà parié.")

    db[uid] -= amount; save_db(db)
    race_bets.append({'user': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"✅ Pari de **{amount}** sur le **#{horse}** accepté.")

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    items = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    mult = 0
    if items[0] == items[1] == items[2]:
        mult = {"7️⃣":100, "💎":50, "🔔":20, "🍇":10, "🍋":5, "🍒":3}[items[0]]
    elif items[0] == items[1] or items[1] == items[2] or items[0] == items[2]: mult = 1.5
    
    s_key = f"{uid}_slot_streak"
    if mult > 0:
        gain = int(amount * mult); profit = gain - amount
        db[uid] += profit
        db[s_key] = db.get(s_key, 0) + 1
        res = f"🎉 **GAGNÉ !** +{gain} coins."
        if db[s_key] >= 7:
            r = discord.utils.get(ctx.guild.roles, name="Hakari")
            if r: await ctx.author.add_roles(r); res += "\n🕺 **JACKPOT HAKARI !**"
    else:
        db[uid] -= amount; db[s_key] = 0; res = "❌ **PERDU.**"
    
    save_db(db)
    await ctx.send(embed=discord.Embed(title="🎰 Slots", description=f"┃ {items[0]} ┃ {items[1]} ┃ {items[2]} ┃\n\n{res}", color=0xFFD700))

# --- AUTRES COMMANDES (ROB, BAL, SHOP) ---
@bot.command()
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return
    db = load_db(); v_bal = db.get(str(member.id), 0)
    if v_bal < 200: return await ctx.send("❌ Trop pauvre.")
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] += stolen; db[str(member.id)] -= stolen
        save_db(db); await ctx.send(f"🥷 **Volé :** {stolen} coins !")
    else:
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - 100)
        save_db(db); await ctx.send("👮 **Échec !** Tu paies 100 coins d'amende.")

@bot.command()
async def bal(ctx, member: discord.Member = None):
    t = member if member else ctx.author; db = load_db()
    await ctx.send(f"💰 **{t.display_name}** : {db.get(str(t.id), 0)} coins")

@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 Shop", color=0x4b41e6)
    for k,v in SHOP_ITEMS.items(): e.add_field(name=k, value=str(v))
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db(); item = item.lower()
    if item not in SHOP_ITEMS: return
    p = SHOP_ITEMS[item]; uid = str(ctx.author.id)
    if db.get(uid, 0) >= p:
        r = discord.utils.find(lambda x: x.name.lower() == item, ctx.guild.roles)
        if r: 
            await ctx.author.add_roles(r)
            db[uid] -= p; save_db(db); await ctx.send(f"✅ Acheté : {r.name}")
        else: await ctx.send("❌ Rôle introuvable.")
    else: await ctx.send("❌ Pas assez d'argent.")

@bot.command(name="helpme")
async def helpme(ctx):
    em = discord.Embed(title="Aide Pandora V4", color=0x4b41e6)
    em.add_field(name="🎰 Jeux", value="`!hilo <mise>` (Nouveau!)\n`!dice <mise>` (Bouton)\n`!slot`, `!race`", inline=False)
    em.add_field(name="💰 Éco", value="`!work` (10min)\n`!daily` (1k-5k)\n`!give` (Taxe 5%)", inline=False)
    await ctx.send(embed=em)

# --- GESTION DES ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        await ctx.send(f"⏳ **Cooldown !** Reviens dans {int(m)}m {int(s)}s.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission.")

keep_alive()
bot.run(os.environ.get('TOKEN'))
