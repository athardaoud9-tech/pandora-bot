import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (POUR RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Le Bot est en ligne !"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURATION ET BASE DE DONNÉES ---
DB_FILE = "database.json"
TAX_RATE = 0.05 # 5% de taxe sur les transferts

# Couleurs
COL_GOLD = 0xFFD700
COL_RED = 0xE74C3C
COL_GREEN = 0x2ECC71
COL_BLUE = 0x3498DB
COL_DARK = 0x2C3E50

# Configuration du Bot (help_command=None retire le double help)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ⚠️ ID DES SALONS (À MODIFIER SI BESOIN)
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914

# --- FONCTIONS UTILITAIRES ---
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def parse_amount(amount_str, balance):
    if str(amount_str).lower() in ["all", "tout"]:
        return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. ÉVÉNEMENTS DISCORD ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Connecté en tant que {bot.user} !")
    print("------ Prêt à fonctionner ------")
    await bot.change_presence(activity=discord.Game(name="!help | Gère ton empire"))

# --- BIENVENUE & DÉPART (NEUTRE) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return

    # Message générique, pas de mention du casino
    desc = f"Bienvenue {member.mention} sur le serveur !\nNous sommes ravis de t'accueillir parmi nous."
    embed = discord.Embed(title="👋 Bienvenue !", description=desc, color=COL_GREEN)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"Membre #{len(member.guild.members)}")
    
    # Gestion image (optionnel)
    file_path = "static/images/background.gif"
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(embed=embed, file=file)
        except:
            await channel.send(embed=embed)
    else:
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if not channel: return

    desc = f"**{member.display_name}** nous a quittés. Bonne continuation !"
    embed = discord.Embed(description=desc, color=COL_DARK)
    
    file_path = "static/images/leave.gif"
    if os.path.exists(file_path):
        try:
            file = discord.File(file_path, filename="leave.gif")
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)
        except:
            await channel.send(embed=embed)
    else:
        await channel.send(embed=embed)

# --- 4. COMMANDE HELP (FIXÉE ET COMPLÈTE) ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📜 MENU D'AIDE", description="Voici toutes les commandes disponibles.", color=COL_BLUE)
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    embed.add_field(name="💰 Économie", value=(
        "`!bal [user]` : Voir le solde\n"
        "`!work` : Travailler (toutes les 10 min)\n"
        "`!daily` : Cadeau quotidien (1k-3k)\n"
        "`!give @user <montant>` : Donner de l'argent (Taxe 5%)\n"
        "`!rob @user` : Tenter de voler quelqu'un"
    ), inline=False)

    embed.add_field(name="🎰 Jeux Casino", value=(
        "`!roulette <mise> <choix>` : Rouge/Noir/Vert/Numéro\n"
        "`!slot <mise>` : Machine à sous (7 wins = Rôle Hakari)\n"
        "`!blackjack <mise>` : Jouer au 21\n"
        "`!dice <mise>` : Dés contre le bot"
    ), inline=False)

    embed.add_field(name="🏆 Compétition", value=(
        "`!race` : Lancer une course de chevaux\n"
        "`!bet <mise> <cheval>` : Parier sur un cheval\n"
        "`!morpion @user <mise>` : Duel de Morpion"
    ), inline=False)

    embed.add_field(name="🛍️ Autres", value=(
        "`!shop` : Voir les rôles à acheter\n"
        "`!buy <item>` : Acheter un objet\n"
        "`!top` : Classement des plus riches"
    ), inline=False)

    embed.set_footer(text="Système Anti-Bug v2.0 • Bon jeu !")
    await ctx.send(embed=embed)

# --- 5. ÉCONOMIE ---
@bot.command(aliases=["top", "rich"])
async def leaderboard(ctx):
    db = load_db()
    users = [(k, v) for k, v in db.items() if k.isdigit() and isinstance(v, (int, float))]
    users.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 CLASSEMENT GÉNÉRAL", color=COL_GOLD)
    desc = ""
    for idx, (uid, bal) in enumerate(users[:10], 1):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name
        except:
            name = "Utilisateur inconnu"
            
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`{idx}.`"
        desc += f"{medal} **{name}** : {int(bal):,} coins\n"
    
    embed.description = desc if desc else "La base de données est vide."
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    db = load_db()
    amount = db.get(str(target.id), 0)
    
    embed = discord.Embed(color=COL_BLUE)
    embed.set_author(name=f"Portefeuille de {target.display_name}", icon_url=target.avatar.url if target.avatar else None)
    embed.description = f"💰 Solde : **{int(amount):,} coins**"
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user) # 10 minutes
async def work(ctx):
    db = load_db()
    gain = random.randint(200, 800)
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    
    embed = discord.Embed(description=f"🔨 Tu as travaillé dur et gagné **{gain} coins** !", color=COL_GREEN)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    db = load_db()
    uid = str(ctx.author.id)
    key_time = f"{uid}_last_daily"
    
    # 86400 = 24h, réglons sur 12h ou 24h selon préférence. Ici 24h pour 'Daily'
    cooldown = 86400 
    last_claim = db.get(key_time, 0)
    
    if time.time() - last_claim < cooldown:
        remaining = cooldown - (time.time() - last_claim)
        h, rem = divmod(remaining, 3600)
        m, s = divmod(rem, 60)
        return await ctx.send(embed=discord.Embed(description=f"⏳ Reviens dans **{int(h)}h {int(m)}m**.", color=COL_RED))
    
    gain = random.randint(1000, 3000)
    db[uid] = db.get(uid, 0) + gain
    db[key_time] = time.time()
    save_db(db)
    
    embed = discord.Embed(title="🎁 Bonus Quotidien", description=f"Tu as reçu **{gain} coins** !", color=COL_GOLD)
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member.id == ctx.author.id: return
    db = load_db()
    uid, tid = str(ctx.author.id), str(member.id)
    bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount:
        return await ctx.send(embed=discord.Embed(description="❌ Fonds insuffisants ou montant invalide.", color=COL_RED))
    
    # Système de taxe
    tax_amount = int(amount * TAX_RATE)
    send_amount = amount - tax_amount
    
    db[uid] -= amount
    db[tid] = db.get(tid, 0) + send_amount
    save_db(db)
    
    embed = discord.Embed(color=COL_GREEN)
    embed.description = f"💸 **{ctx.author.display_name}** a envoyé **{send_amount}** à **{member.display_name}**.\n(Taxe prélevée : {tax_amount} coins)"
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def rob(ctx, member: discord.Member):
    if member == ctx.author or member.bot: return
    db = load_db()
    v_bal = db.get(str(member.id), 0)
    
    if v_bal < 500:
        ctx.command.reset_cooldown(ctx)
        return await ctx.send(embed=discord.Embed(description="❌ Ce membre est trop pauvre, ça ne vaut pas le coup.", color=COL_RED))
    
    if random.random() < 0.4: # 40% de chance de réussite
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.15))
        db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + stolen
        db[str(member.id)] -= stolen
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"🥷 **Réussi !** Tu as volé **{stolen} coins** à {member.display_name} !", color=COL_GREEN))
    else:
        fine = 500
        db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - fine)
        save_db(db)
        await ctx.send(embed=discord.Embed(description=f"👮 **Arrêté !** La police t'a mis une amende de **{fine} coins**.", color=COL_RED))

# --- 6. JEUX CASINO & ROULETTE ---

# ROULETTE (Ajoutée et corrigée)
@bot.command()
async def roulette(ctx, amount_str: str, choice: str):
    db = load_db()
    uid = str(ctx.author.id)
    bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)

    if amount <= 0 or bal < amount:
        return await ctx.send(embed=discord.Embed(description="❌ Mise invalide ou fonds insuffisants.", color=COL_RED))

    # Configuration Roulette
    # 0 = Vert, 1-36 = Rouge/Noir
    red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    
    result = random.randint(0, 36)
    color_res = "vert" if result == 0 else ("rouge" if result in red_numbers else "noir")
    
    win = False
    multiplier = 0
    choice = choice.lower()

    # Vérification gain
    if choice in ["rouge", "red"] and color_res == "rouge":
        win = True; multiplier = 2
    elif choice in ["noir", "black"] and color_res == "noir":
        win = True; multiplier = 2
    elif choice in ["vert", "green"] and color_res == "vert":
        win = True; multiplier = 14
    elif choice.isdigit() and int(choice) == result:
        win = True; multiplier = 36
    
    # Affichage Embed
    embed = discord.Embed(title="🎡 Roulette", color=COL_BLUE)
    color_emoji = "🟢" if result == 0 else ("🔴" if result in red_numbers else "⚫")
    embed.add_field(name="Résultat", value=f"{color_emoji} **{result}** ({color_res.upper()})")

    if win:
        profit = amount * multiplier
        db[uid] += (profit - amount) # On ajoute le profit net
        embed.color = COL_GREEN
        embed.add_field(name="Gagné !", value=f"Tu remportes **{profit} coins** !", inline=False)
    else:
        db[uid] -= amount
        embed.color = COL_RED
        embed.add_field(name="Perdu...", value=f"Tu perds ta mise de {amount} coins.", inline=False)
    
    save_db(db)
    await ctx.send(embed=embed)

# SLOT (Avec Système Hakari)
@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount:
        return await ctx.send(embed=discord.Embed(description="❌ Mise invalide.", color=COL_RED))

    symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
    weights = [30, 25, 20, 15, 10, 5]
    
    col1 = random.choices(symbols, weights=weights, k=1)[0]
    col2 = random.choices(symbols, weights=weights, k=1)[0]
    col3 = random.choices(symbols, weights=weights, k=1)[0]
    
    embed = discord.Embed(title="🎰 Machine à Sous", color=COL_BLUE)
    embed.description = f"🔹 ┃ {col1} ┃ {col2} ┃ {col3} ┃ 🔹"
    
    win = False
    multiplier = 0

    if col1 == col2 == col3:
        win = True
        if col1 == "7️⃣": multiplier = 100
        elif col1 == "💎": multiplier = 50
        elif col1 == "🔔": multiplier = 20
        else: multiplier = 10
    elif col1 == col2 or col2 == col3 or col1 == col3:
        win = True
        multiplier = 1.5

    streak_key = f"{uid}_slot_streak"
    
    if win and multiplier > 1: # On considère victoire si > x1
        winnings = int(amount * multiplier)
        db[uid] += (winnings - amount)
        embed.color = COL_GREEN
        embed.add_field(name="Victoire !", value=f"+{winnings - amount} coins")
        
        # Gestion Streak Hakari
        current_streak = db.get(streak_key, 0) + 1
        db[streak_key] = current_streak
        
        if current_streak >= 7:
            role_name = "Hakari"
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role:
                if role not in ctx.author.roles:
                    await ctx.author.add_roles(role)
                    embed.add_field(name="🕺 JACKPOT HAKARI !", value=f"Tu as gagné 7 fois d'affilée ! Tu reçois le rôle **{role_name}** !", inline=False)
            else:
                embed.set_footer(text=f"Note: Crée le rôle '{role_name}' pour activer le bonus.")
                
    else:
        db[uid] -= amount
        db[streak_key] = 0 # Reset streak
        embed.color = COL_RED
        embed.set_footer(text="Perdu... Streak reset.")

    save_db(db)
    await ctx.send(embed=embed)

# DICE
@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0: return await ctx.send("❌ Mise invalide.")

    p_score = random.randint(1, 6) + random.randint(1, 6)
    b_score = random.randint(1, 6) + random.randint(1, 6)
    
    embed = discord.Embed(title="🎲 Duel de Dés", color=COL_BLUE)
    embed.add_field(name="Toi", value=f"Score: **{p_score}**")
    embed.add_field(name="Bot", value=f"Score: **{b_score}**")
    
    if p_score > b_score:
        db[uid] += amount
        embed.color = COL_GREEN
        embed.description = f"🎉 Tu gagnes **{amount} coins** !"
    elif p_score < b_score:
        db[uid] -= amount
        embed.color = COL_RED
        embed.description = f"❌ Tu perds **{amount} coins**."
    else:
        embed.color = COL_GOLD
        embed.description = "🤝 Égalité, mise remboursée."
        
    save_db(db)
    await ctx.send(embed=embed)

# --- 7. SYSTÈME DE COURSE & RÔLE HOCKEY GENIUS ---
race_in_progress = False
race_bets = []

@bot.command()
async def race(ctx):
    global race_in_progress, race_bets
    if race_in_progress:
        return await ctx.send("🏇 Une course est déjà en cours !")
    
    race_in_progress = True
    race_bets = []
    
    embed = discord.Embed(title="🏇 HIPPODROME", description="La course commence dans **20 secondes** !\nTape `!bet <mise> <cheval 1-5>` pour parier.", color=COL_GREEN)
    msg = await ctx.send(embed=embed)
    
    await asyncio.sleep(20)
    
    if not race_bets:
        race_in_progress = False
        return await ctx.send("❌ Course annulée, aucun pari.")
    
    await ctx.send("🚩 **DÉPART !**")
    
    # Petite animation
    horses = ["🐎", "🦄", "🦓", "🐖", "🐆"]
    progression = [""] * 5
    
    for _ in range(3):
        await asyncio.sleep(1.5)
        desc = ""
        for i in range(5):
            progression[i] += ".." + ("💨" if random.random() > 0.5 else "")
            desc += f"#{i+1} {horses[i]} {progression[i]}\n"
        await msg.edit(embed=discord.Embed(title="🏇 La course est lancée !", description=desc, color=COL_GOLD))
    
    winner = random.randint(1, 5)
    
    # Calcul des gains
    db = load_db()
    result_txt = f"👑 **Le Cheval #{winner} ({horses[winner-1]}) gagne la course !**\n\n"
    
    winners_found = False
    for bet in race_bets:
        if bet['horse'] == winner:
            winners_found = True
            gain = bet['amount'] * 3 # Cote de 3
            uid = str(bet['user_id'])
            db[uid] = db.get(uid, 0) + gain
            result_txt += f"✅ <@{uid}> remporte **{gain} coins** !\n"
            
            # Gestion Role "Hockey Genius" (10 victoires au total)
            win_count_key = f"{uid}_race_wins"
            db[win_count_key] = db.get(win_count_key, 0) + 1
            
            if db[win_count_key] == 10:
                role_name = "Hockey Genius"
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if role:
                    member = ctx.guild.get_member(int(uid))
                    if member and role not in member.roles:
                        await member.add_roles(role)
                        result_txt += f"🏆 **INCROYABLE !** <@{uid}> obtient le rôle **{role_name}** pour ses 10 victoires !\n"

    if not winners_found:
        result_txt += "❌ Personne n'avait parié sur ce cheval."
        
    save_db(db)
    race_in_progress = False
    race_bets = []
    
    await ctx.send(embed=discord.Embed(description=result_txt, color=COL_GOLD))

@bot.command()
async def bet(ctx, amount_str: str, horse: int):
    global race_bets
    if not race_in_progress:
        return await ctx.send("❌ Pas de course en cours. Lance `!race` d'abord.")
    
    if not (1 <= horse <= 5):
        return await ctx.send("❌ Choisis un cheval entre 1 et 5.")
        
    for b in race_bets:
        if b['user_id'] == ctx.author.id:
            return await ctx.send("❌ Tu as déjà parié sur cette course !")
            
    db = load_db()
    uid = str(ctx.author.id)
    bal = db.get(uid, 0)
    amount = parse_amount(amount_str, bal)
    
    if amount <= 0 or bal < amount:
        return await ctx.send("❌ Mise invalide.")
        
    db[uid] -= amount
    save_db(db)
    
    race_bets.append({'user_id': ctx.author.id, 'amount': amount, 'horse': horse})
    await ctx.send(f"🎟️ Pari enregistré : **{amount}** sur le cheval **#{horse}**.")

# --- 8. MORPION (TIC TAC TOE) ---
class MorpionButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="‎", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: MorpionView = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        
        state = view.board[self.y][self.x]
        if state != 0: return

        # Jouer le coup
        player_val = 1 if view.current_player == view.p1 else 2
        view.board[self.y][self.x] = player_val
        
        self.style = discord.ButtonStyle.danger if player_val == 1 else discord.ButtonStyle.success
        self.label = "X" if player_val == 1 else "O"
        self.disabled = True
        
        winner = view.check_winner()
        
        if winner:
            view.stop()
            w_user = view.p1 if winner == 1 else view.p2
            # Paiement
            if view.mise > 0:
                db = load_db()
                db[str(w_user.id)] += view.mise * 2
                save_db(db)
            
            for child in view.children: child.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{w_user.display_name}** a gagné {view.mise * 2} coins !", view=view)
        
        elif all(c != 0 for row in view.board for c in row):
            view.stop()
            # Remboursement
            if view.mise > 0:
                db = load_db()
                db[str(view.p1.id)] += view.mise
                db[str(view.p2.id)] += view.mise
                save_db(db)
            await interaction.response.edit_message(content="🤝 **Match Nul !** Mises remboursées.", view=view)
        
        else:
            view.current_player = view.p2 if view.current_player == view.p1 else view.p1
            await interaction.response.edit_message(content=f"Au tour de {view.current_player.mention}", view=view)

class MorpionView(discord.ui.View):
    def __init__(self, p1, p2, mise):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.current_player = p1
        self.mise = mise
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for y in range(3):
            for x in range(3):
                self.add_item(MorpionButton(x, y))

    def check_winner(self):
        # Lignes & Colonnes
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0: return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0: return self.board[0][i]
        # Diagonales
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0: return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0: return self.board[0][2]
        return None

@bot.command()
async def morpion(ctx, opponent: discord.Member, amount_str: str = "0"):
    if opponent.bot or opponent == ctx.author: return
    db = load_db()
    
    try: mise = int(amount_str)
    except: mise = 0
    
    if mise > 0:
        if db.get(str(ctx.author.id), 0) < mise: return await ctx.send("❌ Tu n'as pas assez d'argent.")
        if db.get(str(opponent.id), 0) < mise: return await ctx.send("❌ L'adversaire n'a pas assez d'argent.")

    # Confirmation View
    view = discord.ui.View()
    accept_btn = discord.ui.Button(label="Accepter", style=discord.ButtonStyle.success)
    
    async def accept_callback(interaction):
        if interaction.user != opponent: return
        # Prélèvement
        if mise > 0:
            db[str(ctx.author.id)] -= mise
            db[str(opponent.id)] -= mise
            save_db(db)
        
        await interaction.response.edit_message(content=f"⚔️ **Morpion** : {ctx.author.mention} vs {opponent.mention} (Mise: {mise})", view=MorpionView(ctx.author, opponent, mise))
    
    accept_btn.callback = accept_callback
    view.add_item(accept_btn)
    
    await ctx.send(f"{opponent.mention}, **{ctx.author.display_name}** te défie au Morpion pour **{mise} coins** !", view=view)

# --- 9. BOUTIQUE ET ADMIN ---
SHOP_ITEMS = {"vip": 5000, "riche": 20000, "roi": 100000}

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 BOUTIQUE", color=COL_BLUE)
    for k, v in SHOP_ITEMS.items():
        embed.add_field(name=k.upper(), value=f"💰 {v:,} coins", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    if item not in SHOP_ITEMS: return await ctx.send("❌ Cet objet n'existe pas.")
    
    price = SHOP_ITEMS[item]
    db = load_db()
    uid = str(ctx.author.id)
    
    if db.get(uid, 0) < price: return await ctx.send("❌ Pas assez d'argent.")
    
    role = discord.utils.get(ctx.guild.roles, name=item) # Le nom du rôle doit être identique (ou ajuste le code)
    if not role: return await ctx.send("❌ Rôle introuvable sur le serveur. Demande à un admin de le créer.")
    
    try:
        await ctx.author.add_roles(role)
        db[uid] -= price
        save_db(db)
        await ctx.send(f"✅ Achat réussi ! Tu as maintenant le rôle **{role.name}**.")
    except:
        await ctx.send("❌ Je n'ai pas la permission de donner ce rôle (vérifie ma hiérarchie).")

# --- 10. GESTION ERREURS GLOBALE ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        await ctx.send(embed=discord.Embed(description=f"⏳ Patiente **{int(m)}m {int(s)}s**.", color=COL_RED), delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argument manquant. Fais `!help`.", delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Mauvais argument (ex: il faut un nombre).", delete_after=5)
    else:
        print(f"Erreur: {error}")

@bot.command()
@commands.has_permissions(administrator=True)
async def admingive(ctx, member: discord.Member, amount: int):
    db = load_db()
    uid = str(member.id)
    
    # Ajout de l'argent
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    
    embed = discord.Embed(
        title="🏦 TRANSFERT ADMINISTRATIF",
        description=f"**{amount:,} coins** ont été ajoutés au compte de {member.mention}.",
        color=COL_GOLD
    )
    embed.set_footer(text=f"Action effectuée par {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

# LANCEMENT
keep_alive()
try:
    bot.run(os.environ['TOKEN'])
except Exception as e:
    print(f"Erreur de token : {e}")
