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
bot = commands.Bot(command_prefix="!", intents=intents)

SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}

@bot.event
async def on_ready():
    print(f"✅ Pandora est Live")

# --- 4. GESTION DES ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        await ctx.send(f"⏳ Calme-toi ! Attends encore **{seconds // 60}min {seconds % 60}s**.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions admin.")

# --- 5. SYSTÈME DE ROB (VOL) ---
@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user) # Cooldown de 30 minutes (1800s)
async def rob(ctx, member: discord.Member):
    if member == ctx.author:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send("❓ Tu ne peux pas te voler toi-même !")

    db = load_db()
    stealer = str(ctx.author.id)
    victim = str(member.id)
    
    victim_bal = db.get(victim, 0)
    
    if victim_bal < 200:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send(f"❌ **{member.display_name}** est trop pauvre pour être volé (min. 200 coins).")

    # 50% de chance de réussir
    success = random.choice([True, False])
    
    if success:
        # Vol entre 10% et 30% du solde de la victime
        stolen_amount = random.randint(int(victim_bal * 0.1), int(victim_bal * 0.3))
        db[stealer] = db.get(stealer, 0) + stolen_amount
        db[victim] = victim_bal - stolen_amount
        save_db(db)
        await ctx.send(f"🥷 **{ctx.author.display_name}** a volé **{stolen_amount} coins** à **{member.display_name}** !")
    else:
        # Amende de 100 coins si on se fait attraper
        fine = 100
        db[stealer] = max(0, db.get(stealer, 0) - fine)
        save_db(db)
        await ctx.send(f"👮 **{ctx.author.display_name}** s'est fait attraper et a payé une amende de **{fine} coins** !")

# --- 6. COMMANDES GIVE & ÉCONOMIE ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"💰 **{amount} coins** donnés à **{member.display_name}**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    gain = random.randint(100, 350)
    db[uid] = db.get(uid, 0) + gain
    save_db(db)
    await ctx.send(f"🔨 Tu as gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_last_daily"
    now = time.time()
    if now - db.get(key, 0) < 43200: # 12h
        reste = int(43200 - (now - db.get(key, 0)))
        return await ctx.send(f"⏳ Reviens dans **{reste // 3600}h {(reste % 3600) // 60}min**.")
    gain = random.randint(500, 1000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = now
    save_db(db)
    await ctx.send(f"🎁 Bonus : **{gain} coins** !")

@bot.command()
async def balance(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, solde : **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 7. BIENVENUE & SHOP ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470176904668516528)
    if channel:
        path = "static/images/background.gif"
        if os.path.exists(path):
            file = discord.File(path, filename="welcome.gif")
            embed = discord.Embed(description=f"🦋 Bienvenue {member.mention}", color=0x4b41e6)
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(file=file, embed=embed)

@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items(): em.add_field(name=it.capitalize(), value=f"💰 {pr}", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item = item.lower().strip()
    if item in SHOP_ITEMS and db.get(uid, 0) >= SHOP_ITEMS[item]:
        role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
        if role:
            db[uid] -= SHOP_ITEMS[item]
            save_db(db)
            await ctx.author.add_roles(role)
            await ctx.send(f"🎉 Rôle **{role.name}** acheté !")
        else: await ctx.send("Rôle introuvable.")
    else: await ctx.send("Pas assez de coins ou article inconnu.")

# --- 8. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
