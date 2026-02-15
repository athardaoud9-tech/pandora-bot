import discord
from discord.ext import commands
import os, time, random, json, asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino V3 est en ligne !"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES ---
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Utilitaire pour transformer "all" ou un nombre en entier
def get_amount(uid, input_str, db):
    balance = db.get(str(uid), 0)
    if input_str.lower() == "all": return balance
    try:
        val = int(input_str)
        return val if val >= 0 else 0
    except: return None

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# CONFIGURATION SERVEUR
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914
SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_WEIGHTS = [35, 30, 22, 12, 6, 3] # Chances augmentées pour Hakari

race_open = False
race_bets = []

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora Connecté !")

# --- 4. BIENVENUE & DÉPART ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        desc = f"🦋 Bienvenue {member.mention} (**{member.display_name}**) !"
        file_p = "static/images/background.gif"
        if os.path.exists(file_p):
            file = discord.File(file_p, filename="welcome.gif")
            emb = discord.Embed(description=desc, color=0x4b41e6)
            emb.set_image(url="attachment://welcome.gif")
            await channel.send(embed=emb, file=file)
        else: await channel.send(desc)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        desc = f"😢 Au revoir **{member.display_name}**..."
        file_p = "static/images/leave.gif"
        if os.path.exists(file_p):
            file = discord.File(file_p, filename="leave.gif")
            emb = discord.Embed(description=desc, color=0xff0000)
            emb.set_image(url="attachment://leave.gif")
            await channel.send(embed=emb, file=file)

# --- 5. JEUX AVEC BOUTONS & "ALL" ---

# --- MORPION AVEC SYSTÈME D'INVITATION ---
class MorpionInvite(discord.ui.View):
    def __init__(self, author, target, amount):
        super().__init__(timeout=60)
        self.author, self.target, self.amount = author, target, amount
    
    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target: return
        db = load_db()
        p1, p2 = str(self.author.id), str(self.target.id)
        if db.get(p1, 0) < self.amount or db.get(p2, 0) < self.amount:
            return await interaction.response.send_message("❌ L'un de vous n'a plus assez d'argent.", ephemeral=True)
        
        db[p1] -= self.amount; db[p2] -= self.amount
        save_db(db)
        self.stop()
        view = TicTacToeView(self.author, self.target, self.amount)
        await interaction.response.edit_message(content=f"🎮 **Duel lancé !** Enjeu : {self.amount*2} coins.", view=view)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target: return
        self.stop()
        await interaction.response.edit_message(content=f"❌ {self.target.display_name} a refusé le duel.", view=None)

class TicTacToeButton(discord.ui.Button["TicTacToeView"]):
    def __init__(self, x, y): super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y); self.x, self.y = x, y
    async def callback(self, interaction):
        view = self.view
        if interaction.user != view.current_player: return
        if self.label != "⬜": return
        self.label = "❌" if view.current_player == view.p1 else "⭕"
        self.style = discord.ButtonStyle.danger if view.current_player == view.p1 else discord.ButtonStyle.success
        view.board[self.y][self.x] = 1 if view.current_player == view.p1 else 2
        view.current_player = view.p2 if view.current_player == view.p1 else view.p1
        if view.check_winner():
            winner = interaction.user; pot = view.amount * 2
            db = load_db(); db[str(winner.id)] = db.get(str(winner.id), 0) + pot; save_db(db)
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{winner.display_name} gagne {pot} coins !**", view=view)
        elif view.is_full():
            db = load_db(); db[str(view.p1.id)] += view.amount; db[str(view.p2.id)] += view.amount; save_db(db)
            await interaction.response.edit_message(content="🤝 Match nul ! Remboursé.", view=None)
        else: await interaction.response.edit_message(content=f"Tour de : {view.current_player.mention}", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(); self.p1, self.p2, self.current_player = p1, p2, p1; self.amount = amount; self.board = [[0]*3 for _ in range(3)]
        for y in range(3):
            for x in range(3): self.add_item(TicTacToeButton(x, y))
    def check_winner(self):
        b = self.board
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != 0: return True
            if b[0][i] == b[1][i] == b[2][i] != 0: return True
        return (b[0][0]==b[1][1]==b[2][2]!=0) or (b[0][2]==b[1][1]==b[2][0]!=0)
    def is_full(self): return all(c != 0 for r in self.board for c in r)

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str = "0"):
    db = load_db()
    amt = get_amount(ctx.author.id, amount_str, db)
    if amt is None: return await ctx.send("❌ Montant invalide.")
    if member == ctx.author or member.bot: return
    
    view = MorpionInvite(ctx.author, member, amt)
    await ctx.send(f"⚔️ {member.mention}, **{ctx.author.display_name}** te défie au Morpion pour **{amt} coins** ! Acceptes-tu ?", view=view)

# --- TOP 5 ---
@bot.command(name="top")
async def top_rich(ctx):
    db = load_db()
    # Filtrer uniquement les clés qui sont des IDs (chiffres) et trier par valeur
    top = sorted([(k, v) for k, v in db.items() if k.isdigit()], key=lambda x: x[1], reverse=True)[:5]
    
    embed = discord.Embed(title="💰 Top 5 des plus riches", color=0xFFD700)
    for i, (uid, bal) in enumerate(top, 1):
        user = bot.get_user(int(uid))
        name = user.name if user else f"Utilisateur {uid}"
        embed.add_field(name=f"{i}. {name}", value=f"**{bal}** coins", inline=False)
    await ctx.send(embed=embed)

# --- SLOT MACHINE ---
@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amt = get_amount(uid, amount_str, db)
    if amt is None or amt <= 0 or db.get(uid, 0) < amt: return await ctx.send("❌ Pas assez d'argent.")
    
    items = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    mult = 0
    if items[0] == items[1] == items[2]:
        mult = {"7️⃣":100, "💎":50, "🔔":20, "🍇":10, "🍋":5, "🍒":3}[items[0]]
    elif items[0] == items[1] or items[1] == items[2] or items[0] == items[2]: mult = 1.5
    
    streak_key = f"{uid}_slot_streak"
    if mult > 0:
        gain = int(amt * mult); db[uid] += (gain - amt)
        db[streak_key] = db.get(streak_key, 0) + 1
        res = f"🎉 **GAGNÉ !** +{gain} coins."
        if db[streak_key] >= 7:
            role = discord.utils.get(ctx.guild.roles, name="Hakari")
            if role: await ctx.author.add_roles(role); res += "\n🕺 **Tu es HAKARI !**"
    else:
        db[uid] -= amt; db[streak_key] = 0; res = "❌ **PERDU.**"
    
    save_db(db)
    await ctx.send(embed=discord.Embed(title="🎰 Machine à sous", description=f"┃ {items[0]} ┃ {items[1]} ┃ {items[2]} ┃\n\n{res}\nSérie : {db.get(streak_key, 0)}/7"))

# --- ADMIN COMMANDS (FIXED) ---
@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount_str: str):
    db = load_db()
    # On autorise "all" ici aussi (même si c'est pour se give sa propre balance, c'est rigolo)
    amt = get_amount(member.id, amount_str, db) if amount_str.lower() != "all" else 1000
    if amount_str.lower() != "all":
        try: amt = int(amount_str)
        except: return await ctx.send("Nombre invalide.")
        
    db[str(member.id)] = db.get(str(member.id), 0) + amt
    save_db(db)
    await ctx.send(f"👑 **{amt} coins** ajoutés à {member.display_name} par l'admin !")

@bot.command(name="give")
async def give(ctx, member: discord.Member, amount_str: str):
    db = load_db(); u1 = str(ctx.author.id); u2 = str(member.id)
    amt = get_amount(u1, amount_str, db)
    if amt is None or amt <= 0 or db.get(u1, 0) < amt: return await ctx.send("❌ Fonds insuffisants.")
    if member == ctx.author: return
    
    db[u1] -= amt; db[u2] = db.get(u2, 0) + amt
    save_db(db)
    await ctx.send(f"💸 **{amt}** envoyés à {member.display_name}.")

# --- COURSE & AUTRES ---
@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open: return
    race_open = True; race_bets = []
    await ctx.send("🏇 **Course ouverte !** Tapez `!bet <mise> <1-5>` (30s)")
    await asyncio.sleep(30)
    if not race_bets: race_open = False; return await ctx.send("Annulé (pas de paris).")
    
    winner = random.randint(1, 5); db = load_db()
    for b in race_bets:
        if b['horse'] == winner:
            gain = b['amt']*2; db[str(b['id'])] = db.get(str(b['id']), 0) + gain
            wins = f"{b['id']}_race_wins"; db[wins] = db.get(wins, 0) + 1
            if db[wins] >= 10:
                role = discord.utils.get(ctx.guild.roles, name="Dompteur de chevaux")
                m = ctx.guild.get_member(b['id'])
                if role and m: await m.add_roles(role)
    save_db(db); race_open = False
    await ctx.send(f"🏁 Le cheval **#{winner}** gagne !")

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_open, race_bets
    if not race_open: return
    db = load_db(); uid = str(ctx.author.id)
    amt = get_amount(uid, amount_str, db)
    if amt is None or amt <= 0 or db.get(uid, 0) < amt: return
    db[uid] -= amt; save_db(db)
    race_bets.append({'id': ctx.author.id, 'amt': amt, 'horse': horse})
    await ctx.send(f"✅ {ctx.author.display_name} parie {amt} sur le {horse}.")

# --- HELP & BASICS ---
@bot.command()
async def bal(ctx): db = load_db(); await ctx.send(f"💰 Solde : **{db.get(str(ctx.author.id), 0)}** coins.")

@bot.command()
async def work(ctx):
    db = load_db(); gain = random.randint(100, 350)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain; save_db(db)
    await ctx.send(f"🔨 +{gain} coins !")

@bot.command(name="helpme")
async def helpme(ctx):
    em = discord.Embed(title="Aide Pandora Casino", color=0x4b41e6)
    em.add_field(name="🎰 Jeux (Supportent 'all')", value="`!slot`, `!blackjack`, `!roulette`, `!morpion @user`, `!race`", inline=False)
    em.add_field(name="💰 Éco", value="`!bal`, `!top`, `!work`, `!give @user <montant>`, `!admin-give @user <montant>`", inline=False)
    await ctx.send(embed=em)

keep_alive()
bot.run(os.environ.get('TOKEN'))
