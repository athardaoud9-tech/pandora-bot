import discord
from discord.ext import commands
import os
import json
import random

# --- CONFIGURATION BASE DE DONNÉES JSON ---
# Remplace la "db" de Replit qui ne marche pas sur Koyeb
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

db = load_db()

# --- SETUP BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

SHOP_ITEMS = {
    "🎰": 100,
    "👑": 500
}

@bot.event
async def on_ready():
    print(f'✅ Bot Pandora prêt sur Koyeb !')

# --- SECTION BOUTIQUE ---
@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items():
        em.add_field(name=it.capitalize(), value=f"💰 {pr}", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, role_name: str):
    n = role_name.lower()
    u_id = str(ctx.author.id)
    user_coins = db.get(u_id, 0) #

    if n not in SHOP_ITEMS or user_coins < SHOP_ITEMS[n]:
        await ctx.send("❌ Tu n'as pas assez de coins ou cet objet n'existe pas.")
        return

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        db[u_id] = user_coins - SHOP_ITEMS[n] #
        save_db(db)
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ Rôle **{role.name}** acheté !")

# --- SECTION ADMIN ---
@bot.command()
@commands.has_permissions(administrator=True)
async def addcoins(ctx, member: discord.Member, amount: int):
    u_id = str(member.id)
    db[u_id] = db.get(u_id, 0) + amount #
    save_db(db)
    await ctx.send(f"✅ **{amount}** coins ajoutés à {member.mention} !")

# --- LANCEMENT ---
# On a supprimé keep_alive() car Koyeb n'en a pas besoin
bot.run(os.environ.get('TOKEN'))
