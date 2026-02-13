import discord
from discord.ext import commands
import os
import time
import random
import datetime
from flask import Flask
from threading import Thread
from replit import db

# --- 1. KEEP ALIVE (24h/24) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIG DU BOT ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}

@bot.event
async def on_ready():
    print(f"✅ Bot Pandora prêt : {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        min, sec = divmod(int(error.retry_after), 60)
        await ctx.send(f"⏳ Calme-toi ! Attends **{min}min {sec}s** avant de recommencer.")

# --- 3. BIENVENUE & DEPART ---
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
        embed = discord.Embed(description=f"👋 {member.display_name} est parti.", color=0xff0000)
        if os.path.exists(path):
            file = discord.File(path, filename="leave.gif")
            embed.set_image(url="attachment://leave.gif")
            await channel.send(file=file, embed=embed)
        else: await channel.send(embed=embed)

# --- 4. ECONOMIE & VOL ---
@bot.command()
async def balance(ctx):
    await ctx.send(f"💰 {ctx.author.mention}, tu as **{db.get(str(ctx.author.id), 0)} coins**.")

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(10, 50)
    u_id = str(ctx.author.id)
    db[u_id] = db.get(u_id, 0) + gain
    await ctx.send(f"🔨 Tu as gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    u_id = str(ctx.author.id)
    key = f"{u_id}_last_daily"
    now = time.time()
    if now - db.get(key, 0) < 86400:
        await ctx.send(f"⏳ Reviens demain !")
    else:
        gain = random.randint(500, 1000)
        db[u_id] = db.get(u_id, 0) + gain
        db[key] = now
        await ctx.send(f"🎁 Cadeau : **{gain} coins** !")

@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user) # 30 min
async def rob(ctx, member: discord.Member):
    u_id, t_id = str(ctx.author.id), str(member.id)
    role_req = discord.utils.get(ctx.guild.roles, name="juif")

    if role_req not in ctx.author.roles:
        ctx.command.reset_cooldown(ctx)
        await ctx.send("❌ Seuls les possesseurs du rôle **Juif** peuvent voler !"); return
    if member.id == ctx.author.id:
        ctx.command.reset_cooldown(ctx); return

    chance = random.randint(1, 100)
    user_coins = db.get(u_id, 0)
    target_coins = db.get(t_id, 0)

    if chance <= 20: # 20% CHANCE PRISON + AMENDE
        amende = min(random.randint(100, 500), user_coins)
        db[u_id] -= amende
        db[t_id] += amende
        try:
            await ctx.author.timeout(datetime.timedelta(minutes=5), reason="Tentative de vol")
            await ctx.send(f"🚔 **PRISON !** {ctx.author.mention} est en cellule pour 5 min et paie **{amende} coins** d'amende à {member.mention} !")
        except:
            await ctx.send(f"🚔 **ALERTE !** Tu paies **{amende} coins** d'amende à {member.mention} (Je n'ai pas pu te mettre en prison).")
        return

    if target_coins <= 0:
        await ctx.send("❌ Rien à voler ici !"); return

    stolen = random.randint(50, min(2000, target_coins))
    db[u_id] += stolen
    db[t_id] -= stolen
    await ctx.send(f"💰 **SUCCÈS !** Tu as dérobé **{stolen} coins** à {member.mention} !")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    u_id, t_id = str(ctx.author.id), str(member.id)
    if amount <= 0 or db.get(u_id, 0) < amount: return
    db[u_id] -= amount; db[t_id] = db.get(t_id, 0) + amount
    await ctx.send(f"💸 **{amount} coins** envoyés à {member.mention} !")

# --- 5. CASINO ---
@bot.command()
async def roulette(ctx, bet: int, color: str):
    u_id, color = str(ctx.author.id), color.lower()
    if color not in ['rouge', 'noir'] or bet <= 0 or db.get(u_id, 0) < bet: return
    db[u_id] -= bet
    res = random.choice(['rouge', 'noir'])
    if color == res:
        db[u_id] += (bet * 2); await ctx.send(f"🎉 GAGNÉ ! (**{res}**). Gain : **{bet*2}** !")
    else: await ctx.send(f"💀 PERDU ! C'était **{res}**.")

@bot.command()
async def blackjack(ctx, bet: int):
    u_id = str(ctx.author.id)
    if bet <= 0 or db.get(u_id, 0) < bet: return
    db[u_id] -= bet
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    p_h, d_h = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]
    def sc(h):
        s = sum(h)
        if s > 21 and 11 in h: h.remove(11); h.append(1); return sc(h)
        return s
    async def msg_bj(f=False):
        em = discord.Embed(title="🃏 Blackjack", color=0x4b41e6)
        em.add_field(name=f"Toi ({sc(p_h)})", value=f"{p_h}")
        em.add_field(name="Dealer", value=f"{d_h if f else [d_h[0], '?']}")
        return em
    m = await ctx.send(embed=await msg_bj())
    while sc(p_h) < 21:
        try:
            r = await bot.wait_for('message', timeout=20.0, check=lambda x: x.author==ctx.author and x.content.lower() in ['hit','stand'])
            if r.content.lower() == 'hit': p_h.append(deck.pop()); await m.edit(embed=await msg_bj())
            else: break
        except: break
    if sc(p_h) > 21: await ctx.send("💥 Bust !"); return
    while sc(d_h) < 17: d_h.append(deck.pop())
    await m.edit(embed=await msg_bj(True))
    if sc(d_h) > 21 or sc(p_h) > sc(d_h):
        db[u_id] += (bet*2); await ctx.send(f"🏆 Gagné ! (**{bet*2}**)")
    elif sc(p_h) == sc(d_h): db[u_id] += bet; await ctx.send("🤝 Égalité.")
    else: await ctx.send("💀 Perdu.")

# --- 6. BOUTIQUE ---
@bot.command()
async def shop(ctx):
    em = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for it, pr in SHOP_ITEMS.items(): em.add_field(name=it.capitalize(), value=f"💰 {pr}", inline=False)
    await ctx.send(embed=em)

@bot.command()
async def buy(ctx, *, role_name: str):
    n = role_name.lower()
    if n not in SHOP_ITEMS or db.get(str(ctx.author.id), 0) < SHOP_ITEMS[n]: return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        db[str(ctx.author.id)] -= SHOP_ITEMS[n]
        await ctx.author.add_roles(role); await ctx.send(f"🎉 Rôle **{role.name}** acheté !")

# --- 7. ADMIN ---
@bot.command()
@commands.has_permissions(administrator=True)
async def addcoins(ctx, member: discord.Member, amount: int):
    db[str(member.id)] = db.get(str(member.id), 0) + amount
    await ctx.send(f"✅ **{amount} coins** ajoutés à {member.mention} !")

# --- 8. RUN ---
keep_alive()
bot.run(os.environ.get('TOKEN'))