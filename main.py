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

# --- 2. BASE DE DONNÉES SÉCURISÉE ---
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

# --- 4. BIENVENUE AVEC GIF (static/images/) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470176904668516528)
    if channel:
        path = "static/images/background.gif" # Chemin GitHub
        embed = discord.Embed(description=f"🦋 Bienvenue {member.mention}", color=0x4b41e6)
        if os.path.exists(path):
            file = discord.File(path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(file=file, embed=embed)
        else:
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1470177322161147914)
    if channel:
        path = "static/images/leave.gif" # Chemin GitHub
        if os.path.exists(path):
            file = discord.File(path, filename="leave.gif")
            await channel.send(content=f"👋 **{member.display_name}** est parti.", file=file)
        else:
            await channel.send(f"👋 **{member.display_name}** est parti.")

# --- 5. ÉCONOMIE ANTI-BUG (Work & Daily) ---
@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    gain = random.randint(100, 350)
    
    # On ajoute et on sauvegarde IMMEDIATEMENT pour éviter le double clic
    db[uid] = db.get(uid, 0) + gain
    save_db(db)
    await ctx.send(f"🔨 **{ctx.author.display_name}**, tu as gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key = f"{uid}_last_daily"
    now = time.time()
    
    # Vérification stricte du temps (24h = 86400s)
    last_claim = db.get(key, 0)
    if now - last_claim < 86400:
        reste = int(86400 - (now - last_claim))
        heures = reste // 3600
        minutes = (reste % 3600) // 60
        return await ctx.send(f"⏳ Reviens dans **{heures}h {minutes}min**.")

    gain = random.randint(500, 1000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = now # Enregistre l'heure actuelle avant d'envoyer le message
    save_db(db)
    await ctx.send(f"🎁 **{ctx.author.display_name}**, tu as reçu ton bonus de **{gain} coins** !")

@bot.command()
async def balance(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, solde : **{db.get(str(ctx.author.id), 0)} coins**.")

# --- 6. SHOP ---
@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items(): em.add_field(name=it.capitalize(), value=f"💰 {pr}", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    item = item.lower().strip()
    if item not in SHOP_ITEMS: return await ctx.send("Article inconnu.")
    prix = SHOP_ITEMS[item]
    if db.get(str(ctx.author.id), 0) < prix: return await ctx.send("Solde insuffisant !")
    
    role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if role:
        db[str(ctx.author.id)] -= prix
        save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"🎉 Rôle **{role.name}** obtenu !")
    else: await ctx.send("Erreur : rôle introuvable.")

# --- 7. LANCEMENT ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
