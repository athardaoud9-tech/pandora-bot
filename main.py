import discord
from discord.ext import commands
import os
import time
import random
import json
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE ---
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

SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora est Live")

# --- 4. GESTION DES ERREURS (FIX COOLDOWN) ---
@bot.event
async def on_command_error(ctx, error):
    # On vérifie si l'erreur est un Cooldown
    if isinstance(error, commands.CommandOnCooldown):
        # On n'envoie le message que si c'est la première fois (Discord gère souvent les doublons)
        seconds = int(error.retry_after)
        minutes = seconds // 60
        secs = seconds % 60
        await ctx.send(f"⏳ **Cooldown !** Reviens dans **{minutes}m {secs}s**.", delete_after=10)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions admin.")

# --- 5. COMMANDE BUY (FIX : ACHAT UNIQUE) ---
@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item = item.lower().strip()
    
    if item not in SHOP_ITEMS:
        return await ctx.send("❌ Cet article n'existe pas.")
    
    prix = SHOP_ITEMS[item]
    
    # Trouver le rôle sur le serveur
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    
    if not role:
        return await ctx.send(f"⚠️ Le rôle **{item}** n'existe pas sur ce serveur.")

    # VERIFICATION : Si l'utilisateur a déjà le rôle
    if role in ctx.author.roles:
        return await ctx.send(f"❌ Tu possèdes déjà le rôle **{role.name}** !")

    # Vérification du solde
    if db.get(uid, 0) < prix:
        return await ctx.send(f"❌ Il te manque **{prix - db.get(uid, 0)} coins** !")
    
    try:
        db[uid] -= prix
        save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"🎉 Félicitations **{ctx.author.display_name}**, tu as acheté **{role.name}** !")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de donner ce rôle (vérifie ma position dans la liste des rôles).")

# --- 6. AUTRES COMMANDES (ROB, GIVE, TAX, etc.) ---
@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❓ Impossible.")
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    if v_bal < 200:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❌ Cible trop pauvre.")
    
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20))
        db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(f"🥷 Tu as volé **{stolen} coins** !")
    else:
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - 100)
        save_db(db)
        await ctx.send("👮 Amende de **100 coins** !")

@bot.command()
async def bal(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, solde : **{db.get(str(ctx.author.id), 0)} coins**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    gain = random.randint(100, 350)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(f"🔨 Tu as gagné **{gain} coins** !")

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
    await ctx.send(f"🎁 +**{gain} coins** !")

# --- 7. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
