import discord
from discord.ext import commands
import os
import time
import random
import json
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (Render) ---
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

# Configuration de la boutique
SHOP_ITEMS = {
    "vip": 1000, 
    "juif": 10000, 
    "milliardaire": 100000
}

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
        await ctx.send("❌ Tu n'as pas les permissions (Admin) pour faire ça.")

# --- 5. COMMANDE GIVE (ADMINS) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"💰 **{ctx.author.display_name}** a donné **{amount} coins** à **{member.display_name}** !")

# --- 6. BIENVENUE & DÉPART (GIFS 2.5MB) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470176904668516528)
    if channel:
        path = "static/images/background.gif"
        embed = discord.Embed(description=f"🦋 Bienvenue {member.mention}", color=0x4b41e6)
        if os.path.exists(path):
            file = discord.File(path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(file=file, embed=embed)
        else: await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1470177322161147914)
    if channel:
        path = "static/images/leave.gif"
        if os.path.exists(path):
            file = discord.File(path, filename="leave.gif")
            await channel.send(content=f"👋 **{member.display_name}** est parti.", file=file)
        else: await channel.send(f"👋 **{member.display_name}** est parti.")

# --- 7. ÉCONOMIE (WORK & DAILY 12H) ---
@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    gain = random.randint(100, 350)
    db[uid] = db.get(uid, 0) + gain
    save_db(db)
    await ctx.send(f"🔨 **{ctx.author.display_name}**, tu as gagné **{gain} coins** !")

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

# --- 8. SHOP & BUY (CORRIGÉ) ---
@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique Pandora", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items(): 
        em.add_field(name=it.capitalize(), value=f"💰 {pr} coins", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item = item.lower().strip()
    
    if item not in SHOP_ITEMS:
        return await ctx.send(f"❌ L'article **{item}** n'existe pas.")
    
    prix = SHOP_ITEMS[item]
    if db.get(uid, 0) < prix:
        return await ctx.send(f"❌ Pas assez de coins !")
    
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if role:
        try:
            db[uid] -= prix
            save_db(db)
            await ctx.author.add_roles(role)
            await ctx.send(f"🎉 **{ctx.author.display_name}**, tu as acheté le rôle **{role.name}** !")
        except:
            await ctx.send("❌ Erreur : Mets mon rôle tout en haut de la liste des rôles !")
    else:
        await ctx.send(f"⚠️ Le rôle **{item}** n'existe pas sur ce serveur.")

# --- 9. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
