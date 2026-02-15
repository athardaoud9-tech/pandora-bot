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

# Dictionnaire du shop bien défini en haut
SHOP_ITEMS = {
    "vip": 1000, 
    "juif": 10000, 
    "milliardaire": 100000
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora est Live")

# --- 4. COMMANDE GIVE (POUR TOUS - VIREMENT) ---
@bot.command(name="give")
async def give_player(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ Montant invalide.")
    if member == ctx.author:
        return await ctx.send("❓ Tu ne peux pas te donner à toi-même.")

    db = load_db()
    uid = str(ctx.author.id)
    target_id = str(member.id)
    
    if db.get(uid, 0) < amount:
        return await ctx.send("❌ Tu n'as pas assez de coins.")

    db[uid] -= amount
    db[target_id] = db.get(target_id, 0) + amount
    save_db(db)
    await ctx.send(f"💸 **{ctx.author.display_name}** a donné **{amount} coins** à **{member.display_name}** !")

# --- 5. COMMANDE ADMIN-GIVE (POUR ADMINS - GÉNÉRER) ---
@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    db = load_db()
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    save_db(db)
    await ctx.send(f"👑 **ADMIN**: **{amount} coins** ajoutés au compte de **{member.display_name}**.")

# --- 6. COMMANDE SHOP (AFFICHAGE FIXÉ) ---
@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛒 Boutique Pandora",
        description="Utilise `!buy <nom>` pour acheter un grade.",
        color=0x4b41e6
    )
    # On boucle sur le dictionnaire pour être sûr qu'il s'affiche
    for name, price in SHOP_ITEMS.items():
        embed.add_field(name=name.upper(), value=f"💰 Price: {price} coins", inline=False)
    
    await ctx.send(embed=embed)

# --- 7. COMMANDE BUY ---
@bot.command()
async def buy(ctx, *, item: str):
    db = load_db()
    uid = str(ctx.author.id)
    item_clean = item.lower().strip()
    
    if item_clean not in SHOP_ITEMS:
        return await ctx.send("❌ Article inconnu.")

    price = SHOP_ITEMS[item_clean]
    role = discord.utils.find(lambda r: r.name.lower() == item_clean, ctx.guild.roles)

    if not role:
        return await ctx.send("⚠️ Erreur: Le rôle n'existe pas sur Discord.")
    if role in ctx.author.roles:
        return await ctx.send("❌ Déjà possédé.")
    if db.get(uid, 0) < price:
        return await ctx.send("❌ Pas assez de coins.")

    db[uid] -= price
    save_db(db)
    await ctx.author.add_roles(role)
    await ctx.send(f"🎉 Tu as acheté le grade **{role.name}** !")

# --- 8. AUTRES (BAL, HELP) ---
@bot.command()
async def bal(ctx):
    db = load_db()
    await ctx.send(f"💰 **{ctx.author.display_name}**, solde : **{db.get(str(ctx.author.id), 0)} coins**.")

@bot.command()
async def help(ctx):
    em = discord.Embed(title="Aide Pandora", color=0x4b41e6)
    em.add_field(name="💰 Éco", value="`!work`, `!daily`, `!bal`, `!give @membre <montant>`", inline=False)
    em.add_field(name="🛒 Shop", value="`!shop`, `!buy <nom>`", inline=False)
    em.add_field(name="🛡️ Admin", value="`!admin-give @membre <montant>`, `!tax @membre <montant>`", inline=False)
    await ctx.send(embed=em)

# --- 9. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
