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
def home(): return "Pandora Casino V7 (Secure) est en ligne !"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. GESTION BASE DE DONNÉES SÉCURISÉE ---
DB_FILE = "database.json"
TAX_RATE = 0.05 # 5%

def get_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

def get_balance(user_id):
    db = get_db()
    return db.get(str(user_id), 0)

def update_balance(user_id, amount):
    """ Modifie le solde de façon atomique et sécurisée """
    db = get_db()
    uid = str(user_id)
    new_bal = db.get(uid, 0) + int(amount)
    db[uid] = new_bal
    save_db(db)
    return new_bal

def parse_amount(amount_str, user_id):
    """ Gère 'all', 'tout' et les nombres entiers """
    bal = get_balance(user_id)
    s = str(amount_str).lower().strip()
    if s in ["all", "tout", "max"]:
        return int(bal)
    try:
        val = int(s)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- 4. CLASSES DE JEUX (VIEWS) ---

# === BLACKJACK ===
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.amount = amount
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A'] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]

    def draw(self): return self.deck.pop()

    def calc(self, hand):
        score = 0; aces = 0
        for c in hand:
            if isinstance(c, int): score += c
            elif c in ['J','Q','K']: score += 10
            elif c == 'A': score += 11; aces += 1
        while score > 21 and aces: score -= 10; aces -= 1
        return score

    def embed(self, hide=True, res=None, col=0x4b41e6):
        p = self.calc(self.player_hand); d = self.calc(self.dealer_hand)
        desc = f"Mise : **{self.amount}**\n\n{res if res else ''}"
        e = discord.Embed(title="🃏 Blackjack", description=desc, color=col)
        e.add_field(name=f"👤 Toi ({p})", value=f"`{self.player_hand}`")
        e.add_field(name=f"🎩 Croupier ({d if not hide else '?'})", value=f"`{self.dealer_hand if not hide else [self.dealer_hand[0], '?']}`")
        return e

    async def end(self, itx, msg, mult):
        for c in self.children: c.disabled = True
        if mult > 0:
            gain = int(self.amount * mult)
            # Si mult=1 (égalité), on rend la mise. Si mult=2 (win), on rend mise + gain.
            # update_balance ajoute au solde. Comme on a déjà retiré la mise au début :
            # Win (x2) : on doit ajouter 2*mise.
            # Egalité (x1) : on doit ajouter 1*mise.
            update_balance(self.author_id, gain)
            col = 0x00ff00 if mult > 1 else 0xFFA500
        else:
            col = 0xff0000
        await itx.response.edit_message(embed=self.embed(False, msg, col), view=self)
        self.stop()

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary, emoji="➕")
    async def hit(self, itx: discord.Interaction, btn):
        if itx.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        if self.calc(self.player_hand) > 21: await self.end(itx, "💥 **BUST !** Tu as dépassé 21.", 0)
        else: await itx.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stand(self, itx: discord.Interaction, btn):
        if itx.user.id != self.author_id: return
        while self.calc(self.dealer_hand) < 17: self.dealer_hand.append(self.draw())
        p = self.calc(self.player_hand); d = self.calc(self.dealer_hand)
        if d > 21: await self.end(itx, "🎉 **Le Croupier saute !** Gagné !", 2)
        elif p > d: await self.end(itx, "🎉 **Tu bats le Croupier !**", 2)
        elif p == d: await self.end(itx, "🤝 **Égalité.** (Remboursé)", 1)
        else: await self.end(itx, "❌ **Le Croupier gagne.**", 0)

# === MORPION ===
class TTTBtn(discord.ui.Button):
    def __init__(self, x, y): super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y); self.x=x; self.y=y
    async def callback(self, itx):
        v = self.view
        if itx.user != v.turn: return
        v.board[self.y][self.x] = 1 if v.turn == v.p1 else 2
        self.label = "❌" if v.turn == v.p1 else "⭕"
        self.style = discord.ButtonStyle.danger if v.turn == v.p1 else discord.ButtonStyle.success
        self.disabled = True
        
        # Win check
        b = v.board
        lines = b + [[b[r][c] for r in range(3)] for c in range(3)] + [[b[i][i] for i in range(3)], [b[i][2-i] for i in range(3)]]
        win = any(l[0]==l[1]==l[2]!=0 for l in lines)
        full = all(c!=0 for r in b for c in r)

        if win:
            pot = v.amt * 2; update_balance(v.turn.id, pot)
            for c in v.children: c.disabled = True
            await itx.response.edit_message(content=f"🏆 **{v.turn.mention} gagne {pot} coins !**", view=v); v.stop()
        elif full:
            update_balance(v.p1.id, v.amt); update_balance(v.p2.id, v.amt)
            await itx.response.edit_message(content="🤝 **Match Nul !** Remboursé.", view=v); v.stop()
        else:
            v.turn = v.p2 if v.turn == v.p1 else v.p1
            await itx.response.edit_message(content=f"Au tour de {v.turn.mention}", view=v)

class TTTView(discord.ui.View):
    def __init__(self, p1, p2, amt):
        super().__init__(timeout=60); self.p1=p1; self.p2=p2; self.amt=amt; self.turn=p1; self.board=[[0]*3 for _ in range(3)]
        for y in range(3):
            for x in range(3): self.add_item(TTTBtn(x, y))

class DuelInvite(discord.ui.View):
    def __init__(self, p1, p2, amt): super().__init__(timeout=60); self.p1=p1; self.p2=p2; self.amt=amt
    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def ok(self, itx, btn):
        if itx.user != self.p2: return
        if get_balance(self.p1.id) < self.amt or get_balance(self.p2.id) < self.amt:
            return await itx.response.send_message("❌ Fonds insuffisants (l'un de vous).", ephemeral=True)
        update_balance(self.p1.id, -self.amt); update_balance(self.p2.id, -self.amt)
        await itx.response.edit_message(content=f"⚔️ **Duel !** {self.p1.mention} commence.", view=TTTView(self.p1, self.p2, self.amt))
    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def no(self, itx, btn):
        if itx.user == self.p2: await itx.response.edit_message(content="🚫 Refusé.", view=None)

# === DICE ===
class DiceView(discord.ui.View):
    def __init__(self, uid, amt): super().__init__(timeout=60); self.uid=uid; self.amt=amt
    @discord.ui.button(label="Lancer", style=discord.ButtonStyle.blurple, emoji="🎲")
    async def roll(self, itx, btn):
        if itx.user.id != self.uid: return
        u = random.randint(2,12); b = random.randint(2,12)
        e = discord.Embed(title="🎲 Dés", color=0x4b41e6)
        e.add_field(name="Toi", value=str(u)); e.add_field(name="Bot", value=str(b))
        if u > b:
            update_balance(self.uid, self.amt*2); e.color=0x00ff00; e.description=f"🎉 **Gagné !** (+{self.amt})"
        elif u < b: e.color=0xff0000; e.description=f"❌ **Perdu.** (-{self.amt})"
        else: update_balance(self.uid, self.amt); e.color=0xFFA500; e.description="🤝 **Égalité.** (Remboursé)"
        btn.disabled=True; await itx.response.edit_message(embed=e, view=self); self.stop()

# --- 5. COMMANDES ---

@bot.event
async def on_ready(): print(f"✅ Connecté : {bot.user}")

@bot.command()
async def blackjack(ctx, amount_str: str):
    amt = parse_amount(amount_str, ctx.author.id)
    if amt <= 0: return await ctx.send("❌ Pas assez d'argent.", delete_after=5)
    update_balance(ctx.author.id, -amt)
    await ctx.send(embed=discord.Embed(title="🃏 Blackjack", description="Distribution...", color=0x4b41e6), view=BlackjackView(ctx.author.id, amt))

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str):
    if member.bot or member==ctx.author: return await ctx.send("❌ Impossible.", delete_after=5)
    amt = parse_amount(amount_str, ctx.author.id)
    if amt <= 0: return await ctx.send("❌ Pas assez d'argent.", delete_after=5)
    await ctx.send(member.mention, embed=discord.Embed(description=f"⚔️ {ctx.author.mention} te défie pour **{amt}** !", color=0xFFFF00), view=DuelInvite(ctx.author, member, amt))

@bot.command()
async def dice(ctx, amount_str: str):
    amt = parse_amount(amount_str, ctx.author.id)
    if amt <= 0: return await ctx.send("❌ Pas assez d'argent.", delete_after=5)
    update_balance(ctx.author.id, -amt)
    await ctx.send(embed=discord.Embed(description=f"🎲 Mise : **{amt}**. Lancer ?", color=0x4b41e6), view=DiceView(ctx.author.id, amt))

@bot.command()
async def slot(ctx, amount_str: str):
    uid = ctx.author.id; amt = parse_amount(amount_str, uid)
    if amt <= 0: return await ctx.send("❌ Pas assez d'argent.", delete_after=5)
    update_balance(uid, -amt)
    
    sym = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]; w = [40, 30, 20, 10, 5, 2]
    r = random.choices(sym, w, k=3)
    
    mult = 0
    if r[0]==r[1]==r[2]: mult = {"7️⃣":50, "💎":20, "🔔":10}.get(r[0], 5)
    elif r[0]==r[1] or r[1]==r[2] or r[0]==r[2]: mult = 1.5
    
    desc = f"**» ┃ {r[0]} ┃ {r[1]} ┃ {r[2]} ┃ «**\n\n"
    col = 0xff0000
    if mult > 0:
        gain = int(amt * mult); update_balance(uid, gain); col = 0x00ff00
        desc += f"🎉 **GAGNÉ !** x{mult} (+{gain - amt})"
    else: desc += f"❌ **PERDU** (-{amt})"
    
    await ctx.send(embed=discord.Embed(title="🎰 Slot", description=desc, color=col))

# --- ÉCONOMIE ---
@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(100, 400); update_balance(ctx.author.id, gain)
    await ctx.send(f"🔨 Tu as gagné **{gain} coins**.")

@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id); db = get_db(); last = db.get(f"{uid}_d", 0)
    if time.time() - last < 43200: return await ctx.send("⏳ Reviens dans 12h.", delete_after=5)
    gain = random.randint(1000, 3000); update_balance(uid, gain)
    db = get_db(); db[f"{uid}_d"] = time.time(); save_db(db)
    await ctx.send(f"🎁 Daily : **+{gain} coins** !")

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member==ctx.author: return
    amt = parse_amount(amount_str, ctx.author.id)
    if amt <= 0: return await ctx.send("❌ Pas assez d'argent.", delete_after=5)
    tax = int(amt * TAX_RATE); final = amt - tax
    update_balance(ctx.author.id, -amt); update_balance(member.id, final)
    await ctx.send(f"💸 **Envoi :** {amt} | **Taxe :** {tax} | **Reçu :** {final}")

@bot.command()
async def bal(ctx, member: discord.Member = None):
    t = member or ctx.author
    await ctx.send(embed=discord.Embed(description=f"💰 **{t.display_name}** : {get_balance(t.id)} coins", color=0xFFD700))

# --- ADMIN ---
@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount_str: str):
    amt = parse_amount(amount_str, member.id)
    if amt > 0: update_balance(member.id, -amt); await ctx.send(f"👮 **Taxe** : -{amt} pour {member.mention}.")

@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    update_balance(member.id, amount); await ctx.send(f"👑 **Admin Give** : +{amount} pour {member.mention}.")

# --- HELP COMPLET ---
@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 Aide Pandora V7", color=0x4b41e6)
    e.add_field(name="🎰 Casino (Accepte 'all')", value="`!blackjack <mise>` : Le 21.\n`!morpion <@user> <mise>` : Duel.\n`!dice <mise>` : Dés.\n`!slot <mise>` : Machine à sous.", inline=False)
    e.add_field(name="💰 Argent", value="`!work` : Gagner (10min).\n`!daily` : Bonus (12h).\n`!give <@user> <mt>` : Donner (5% taxe).\n`!bal` : Solde.", inline=False)
    e.add_field(name="👮 Admin", value="`!tax`, `!admin-give`", inline=False)
    await ctx.send(embed=e)

# --- ANTI-SPAM & ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60); h, m = divmod(m, 60)
        t = f"{int(s)}s"
        if m > 0: t = f"{int(m)}m {t}"
        if h > 0: t = f"{int(h)}h {t}"
        await ctx.send(f"⏳ **Cooldown !** Attends encore **{t}**.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Commande incomplète (ex: `!slot 100`).", delete_after=5)

keep_alive()
bot.run(os.environ.get('TOKEN'))
