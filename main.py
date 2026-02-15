import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Bot est en ligne !"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES ---
DB_FILE = "database.json"
COL_GOLD, COL_RED, COL_GREEN, COL_BLUE = 0xFFD700, 0xFF0033, 0x00FF00, 0x4B41E6

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
        return {}
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

def parse_amount(amount_str, balance):
    if str(amount_str).lower() in ["all", "tout"]: return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except: return 0

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
# On désactive explicitement le help_command de base ici
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914
SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
race_open = False
race_bets = [] 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} est prêt !")

# --- 4. BIENVENUE & DÉPART (NEUTRE) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="👋 Bienvenue !", description=f"Ravi de te voir parmi nous {member.mention} !\nN'hésite pas à consulter le règlement.", color=COL_GREEN)
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(description=f"**{member.display_name}** a quitté le serveur. À bientôt !", color=COL_RED)
    await channel.send(embed=embed)

# --- 5. HELP (UNIQUE ET COMPLET) ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 LISTE DES COMMANDES", color=COL_BLUE)
    embed.add_field(name="💰 Économie", value="`!bal`, `!work` (10m), `!daily`, `!give`, `!top`, `!rob`", inline=False)
    embed.add_field(name="🎰 Casino", value="`!slot <mise>`, `!blackjack <mise>`, `!roulette <mise> <couleur>`, `!dice <mise>`", inline=False)
    embed.add_field(name="🎮 Jeux", value="`!morpion @user <mise>`, `!race`, `!bet <mise> <cheval>`", inline=False)
    embed.add_field(name="⚙️ Staff", value="`!admingive`, `!tax`, `!shop`, `!buy`", inline=False)
    await ctx.send(embed=embed)

# --- 6. ROULETTE (RÉPARÉE) ---
@bot.command()
async def roulette(ctx, amount_str: str, color: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    color = color.lower()

    if color not in ["rouge", "noir", "red", "black"]:
        return await ctx.send("❌ Choisis une couleur : **rouge** ou **noir**.")
    if amount <= 0 or bal < amount:
        return await ctx.send("❌ Fonds insuffisants.")

    # Logique
    win_color = random.choice(["rouge", "noir"])
    is_win = (color in ["rouge", "red"] and win_color == "rouge") or (color in ["noir", "black"] and win_color == "noir")

    if is_win:
        db[uid] += amount
        emb = discord.Embed(title="🎰 Roulette", description=f"C'est tombé sur **{win_color.upper()}** !\n\n🎉 **Tu gagnes {amount * 2} coins !**", color=COL_GREEN)
    else:
        db[uid] -= amount
        emb = discord.Embed(title="🎰 Roulette", description=f"C'est tombé sur **{win_color.upper()}** !\n\n❌ **Tu as perdu {amount} coins.**", color=COL_RED)
    
    save_db(db)
    await ctx.send(embed=emb)

# --- 7. ÉCONOMIE & ADMIN ---
@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db(); gain = random.randint(100, 500)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db); await ctx.send(f"🔨 +{gain} coins !")

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_d"
    if time.time() - db.get(key, 0) < 43200: return await ctx.send("⏳ Reviens plus tard !")
    gain = random.randint(1000, 3000); db[uid] = db.get(uid, 0) + gain
    db[key] = time.time(); save_db(db); await ctx.send(f"🎁 Daily : +{gain} !")

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db(); db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db); await ctx.send(f"✅ {amount} ajoutés à {member.display_name}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id); bal = db.get(uid, 0)
    loss = min(amount, bal); db[uid] -= loss; save_db(db)
    await ctx.send(f"⚖️ {member.display_name} a été taxé de {loss} coins.")

@bot.command()
async def bal(ctx, member: discord.Member = None):
    t = member if member else ctx.author; db = load_db()
    await ctx.send(f"💰 **{t.display_name}** : {db.get(str(t.id), 0)} coins.")

# --- 8. SLOTS (AVEC RÔLE HAKARI) ---
@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    if amount <= 0 or bal < amount: return await ctx.send("❌ Argent insuffisant.")

    res = random.choices(SLOT_SYMBOLS, k=3)
    win = (res[0] == res[1] == res[2])
    streak_key = f"{uid}_stk"

    if win:
        db[uid] += amount * 10
        stk = db.get(streak_key, 0) + 1; db[streak_key] = stk
        msg = f"🎉 GAGNÉ ! (Streak: {stk}/7)"
        if stk >= 7:
            r = discord.utils.get(ctx.guild.roles, name="Hakari")
            if r: await ctx.author.add_roles(r); msg += "\n🕺 **Rôle HAKARI obtenu !**"
    else:
        db[uid] -= amount; db[streak_key] = 0
        msg = "❌ PERDU."

    save_db(db)
    await ctx.send(f"{' | '.join(res)}\n{msg}")

# --- 9. RACES (AVEC RÔLE JOCKEY GENIUS) ---
@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return await ctx.send("Course en cours !")
    race_open = True; race_bets = []
    await ctx.send("🏇 **Course lancée !** `!bet <mise> <1-5>` (30s)")
    await asyncio.sleep(30)
    if not race_bets: race_open = False; return await ctx.send("Annulé (0 paris).")
    
    winner = random.randint(1, 5); db = load_db(); res_txt = f"👑 Cheval #{winner} gagne !\n"
    for b in race_bets:
        if b['h'] == winner:
            db[str(b['u'])] += b['a'] * 2
            w_key = f"{b['u']}_rw"
            db[w_key] = db.get(w_key, 0) + 1
            if db[w_key] >= 10:
                r = discord.utils.get(ctx.guild.roles, name="Jockey Genius")
                u = ctx.guild.get_member(b['u'])
                if r and u: await u.add_roles(r); res_txt += f"🏅 <@{b['u']}> est un **Jockey Genius** !\n"
            res_txt += f"✅ <@{b['u']}> gagne !\n"
    
    save_db(db); race_open = False; await ctx.send(res_txt)

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_open, race_bets
    db = load_db(); uid = str(ctx.author.id); bal = db.get(uid, 0)
    amt = parse_amount(amount_str, bal)
    if not race_open or amt <= 0 or bal < amt or not (1<=horse<=5): return await ctx.send("Erreur pari.")
    db[uid] -= amt; save_db(db)
    race_bets.append({'u': ctx.author.id, 'a': amt, 'h': horse})
    await ctx.send("✅ Pari enregistré.")

# --- AUTRES JEUX (BLACKJACK, DICE, MORPION) ---
# [Garder le code des versions précédentes pour ces fonctions, ils sont stables]

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Attends {int(error.retry_after)}s.", delete_after=5)

keep_alive()
bot.run(os.environ.get('TOKEN'))
