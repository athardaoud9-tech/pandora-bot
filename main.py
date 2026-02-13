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
    print(f"✅ Pandora est Live")

# --- 4. GESTION DES ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        await ctx.send(f"⏳ Attends encore **{seconds // 60}min {seconds % 60}s**.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Permission insuffisante.")

# --- 5. COMMANDE HELP ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 Aide - Pandora", color=0x4b41e6)
    embed.add_field(name="💰 Économie", value="`!work`, `!daily`, `!bal`, `!rob @membre`", inline=False)
    embed.add_field(name="🛒 Boutique", value="`!shop`, `!buy <nom>`", inline=False)
    embed.add_field(name="🛡️ Admin", value="`!give @membre <montant>`, `!tax @membre <montant>`", inline=False)
    await ctx.send(embed=embed)

# --- 6. COMMANDE TAX (ADMIN) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    current_bal = db.get(uid, 0)
    
    if current_bal <= 0:
        return await ctx.send(f"❌ **{member.display_name}** n'a déjà plus d'argent.")
    
    tax_amount = min(amount, current_bal) # On ne peut pas taxer plus que ce qu'il a
    db[uid] = current_bal - tax_amount
    save_db(db)
    
    await ctx.send(f"💸 **L'État a taxé {tax_amount} coins** à **{member.display_name}** !")

# --- 7. SYSTÈME DE ROB (MAX 20%) ---
@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❓ Tu ne peux pas te voler toi-même.")
    
    db = load_db()
    victim_bal = db.get(str(member.id), 0)
    
    if victim_bal < 200:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send(f"❌ **{member.display_name}** est trop pauvre (min. 200 coins).")
    
    if random.choice([True, False]):
        # Vol entre 5% et 20% du solde maximum
        stolen = random.randint(int(victim_bal * 0.05), int(victim_bal * 0.20))
        db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(f"🥷 Succès ! Tu as dérobé **{stolen} coins** (max 20%) à **{member.display_name}** !")
    else:
        fine = 100
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(f"👮 Raté ! Tu as été dénoncé et payes une amende de **{fine} coins**.")

# --- 8. AUTRES COMMANDES ÉCO ---
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
    await ctx.send(f"🎁 Bonus : **{gain} coins** !")

@bot.command()
async def bal(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, solde : **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 9. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
