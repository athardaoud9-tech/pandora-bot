import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino est en ligne !"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES & UTILITAIRES ---
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

# Fonction pour gérer "all" ou un nombre
def parse_amount(amount_str, balance):
    if str(amount_str).lower() in ["all", "tout"]:
        return int(balance)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# SALONS (A MODIFIER SI BESOIN)
WELCOME_CHANNEL_ID = 1470176904668516528 
LEAVE_CHANNEL_ID = 1470177322161147914

# CONFIGURATION JEUX
SHOP_ITEMS = {"vip": 1000, "juif": 10000, "milliardaire": 100000}
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 20, 15, 8, 2] 

# VARIABLES GLOBALES COURSE
race_open = False
race_bets = [] 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Pandora est prêt en tant que {bot.user} !")

# --- 4. BIENVENUE & DÉPART ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        file_path = "static/images/background.gif"
        desc = f"🦋 Bienvenue {member.mention} (**{member.display_name}**) sur le serveur !"
        if os.path.exists(file_path):
            file = discord.File(file_path, filename="welcome.gif")
            embed = discord.Embed(description=desc, color=0x4b41e6)
            embed.set_image(url="attachment://welcome.gif")
            await channel.send(embed=embed, file=file)
        else: await channel.send(desc)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        file_path = "static/images/leave.gif"
        desc = f"😢 Au revoir **{member.display_name}**..."
        if os.path.exists(file_path):
            file = discord.File(file_path, filename="leave.gif")
            embed = discord.Embed(description=desc, color=0xff0000)
            embed.set_image(url="attachment://leave.gif")
            await channel.send(embed=embed, file=file)

# --- 5. SYSTÈME ÉCONOMIE & ADMIN ---

@bot.command(aliases=["top", "richest"])
async def leaderboard(ctx):
    db = load_db()
    # On filtre pour ne garder que les clés qui sont des ID utilisateurs (chiffres)
    # et on exclut les stats comme "_streak" ou "_wins"
    users = []
    for key, value in db.items():
        if key.isdigit() and isinstance(value, int):
            users.append((key, value))
    
    # Tri décroissant
    users.sort(key=lambda x: x[1], reverse=True)
    top_5 = users[:5]

    embed = discord.Embed(title="🏆 Top 5 - Les plus riches", color=0xFFD700)
    
    desc = ""
    for idx, (uid, bal) in enumerate(top_5, 1):
        user = bot.get_user(int(uid))
        name = user.display_name if user else "Inconnu"
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        desc += f"**{medal} {name}** : {bal} coins\n"
    
    embed.description = desc if desc else "Personne n'a d'argent..."
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member.id == ctx.author.id:
        return await ctx.send("❌ Tu ne peux pas donner à un bot ou à toi-même.")
    
    db = load_db()
    author_id = str(ctx.author.id)
    target_id = str(member.id)
    
    balance = db.get(author_id, 0)
    amount = parse_amount(amount_str, balance)

    if amount <= 0:
        return await ctx.send("❌ Montant invalide.")
    if balance < amount:
        return await ctx.send(f"❌ Tu n'as pas assez d'argent (Solde: {balance}).")

    db[author_id] -= amount
    db[target_id] = db.get(target_id, 0) + amount
    save_db(db)
    
    await ctx.send(f"💸 **{ctx.author.display_name}** a donné **{amount} coins** à **{member.display_name}** !")

@bot.command(aliases=["admingive"])
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    """Donne de l'argent (création) sans en retirer à l'admin"""
    db = load_db()
    uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"✅ **ADMIN:** {amount} coins ajoutés au compte de {member.mention}.")

# --- 6. JEUX ---

# --- MULTI-JOUEUR COURSE (RACE) ---
@bot.command()
async def race(ctx):
    global race_open, race_bets
    if race_open:
        return await ctx.send("🏇 Une course est déjà en préparation ! Faites `!bet <mise> <cheval>` !")
    
    race_open = True
    race_bets = []
    
    embed = discord.Embed(title="🏇 Hippodrome Pandora", description="Une nouvelle course va démarrer dans **30 secondes** !", color=0x00ff00)
    embed.add_field(name="Comment participer ?", value="Tape `!bet <mise> <cheval (1-5)>`\nExemple: `!bet 100 4` ou `!bet all 2`", inline=False)
    await ctx.send(embed=embed)
    
    await asyncio.sleep(30)
    
    if not race_bets:
        race_open = False
        return await ctx.send("❌ Personne n'a parié. Course annulée.")
    
    # Lancement de la course
    msg = await ctx.send(f"🚫 **Les paris sont fermés !** Départ imminent...")
    await asyncio.sleep(1)
    
    # Animation simple
    track = "🏇 🏇 🏇 🏇 🏇"
    anim_embed = discord.Embed(title="🏇 La course est lancée !", description="Les chevaux s'élancent !", color=0x00ff00)
    anim_embed.add_field(name="Piste", value="1. 🏇\n2. 🏇\n3. 🏇\n4. 🏇\n5. 🏇")
    await msg.edit(content="", embed=anim_embed)
    
    await asyncio.sleep(2)
    anim_embed.description = "🌬️ Ils sont dans le dernier virage... Quel suspense !"
    # Random wind effect visualization
    anim_embed.set_field_at(0, name="Piste", value=f"1. {'💨' if random.random()>0.5 else '🏇'}\n2. 🏇\n3. 🏇\n4. {'💨' if random.random()>0.5 else '🏇'}\n5. 🏇")
    await msg.edit(embed=anim_embed)
    await asyncio.sleep(2)
    
    # Résultat
    winner = random.randint(1, 5)
    result_text = f"👑 Le cheval **#{winner}** remporte la course !\n\n"
    
    db = load_db()
    winners_list = []
    
    for bet in race_bets:
        uid = str(bet['user_id'])
        if bet['horse'] == winner:
            gain = bet['amount'] * 2
            db[uid] = db.get(uid, 0) + gain
            
            # Gestion Role Dompteur (10 victoires)
            wins_key = f"{uid}_race_wins"
            db[wins_key] = db.get(wins_key, 0) + 1
            
            user = ctx.guild.get_member(int(uid))
            u_name = user.display_name if user else "Inconnu"
            winners_list.append(f"✅ **{u_name}** gagne {gain} coins !")
            
            if db[wins_key] >= 10:
                role = discord.utils.get(ctx.guild.roles, name="Dompteur de chevaux")
                if role and user and role not in user.roles:
                    await user.add_roles(role)
                    result_text += f"\n🏅 **{u_name}** devient **Dompteur de chevaux** !"

    save_db(db)
    
    if len(winners_list) > 0:
        result_text += "\n".join(winners_list)
    else:
        result_text += "❌ Personne n'avait parié sur ce cheval..."

    final_embed = discord.Embed(title="🏁 Résultat Final", description=result_text, color=0xFFD700)
    final_embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/horse-racing_1f3c7.png")
    await msg.edit(embed=final_embed)
    
    race_open = False
    race_bets = []

@bot.command()
async def bet(ctx, amount_str: str, horse_num: int):
    global race_open, race_bets
    if not race_open:
        return await ctx.send("❌ Aucune course en préparation. Tape `!race` pour en lancer une !")
    
    if horse_num < 1 or horse_num > 5:
        return await ctx.send("❌ Choisis un cheval entre 1 et 5.")

    db = load_db()
    uid = str(ctx.author.id)
    balance = db.get(uid, 0)
    amount = parse_amount(amount_str, balance)
    
    if amount <= 0 or balance < amount:
        return await ctx.send("❌ Fonds insuffisants ou mise invalide.")

    # Vérifier si déjà parié
    for b in race_bets:
        if b['user_id'] == ctx.author.id:
            return await ctx.send("❌ Tu as déjà parié sur cette course !")

    # Retirer l'argent immédiatement
    db[uid] -= amount
    save_db(db)
    
    race_bets.append({'user_id': ctx.author.id, 'amount': amount, 'horse': horse_num})
    await ctx.send(f"🎟️ **{ctx.author.display_name}** a misé **{amount}** sur le cheval **#{horse_num}** !")

# --- SLOT MACHINE (HAKARI) ---
@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db()
    uid = str(ctx.author.id)
    balance = db.get(uid, 0)
    amount = parse_amount(amount_str, balance)
    
    streak_key = f"{uid}_slot_streak"
    
    if amount <= 0 or balance < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    items = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    multiplier = 0
    
    # Calcul Multiplicateur
    if items[0] == items[1] == items[2]:
        sym = items[0]
        if sym == "7️⃣": multiplier = 100
        elif sym == "💎": multiplier = 50
        elif sym == "🔔": multiplier = 20
        elif sym == "🍇": multiplier = 10
        elif sym == "🍋": multiplier = 5
        elif sym == "🍒": multiplier = 3
    elif items[0] == items[1] or items[1] == items[2] or items[0] == items[2]:
        multiplier = 1.5
    
    desc_res = f"**»** ┃ {items[0]} ┃ {items[1]} ┃ {items[2]} ┃ **«**"

    if multiplier > 0:
        winnings = int(amount * multiplier)
        profit = winnings - amount
        db[uid] = db.get(uid, 0) + profit
        
        # Gestion Streak Hakari
        current_streak = db.get(streak_key, 0) + 1
        db[streak_key] = current_streak
        
        msg_streak = f"\n🔥 Série de victoires : **{current_streak}/7**"
        
        if current_streak >= 7:
            role = discord.utils.get(ctx.guild.roles, name="Hakari")
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                msg_streak += "\n🕺 **JACKPOT ! Tu obtiens le rôle HAKARI !**"
            else:
                msg_streak += "\n(Tu es déjà Hakari !)"
        
        save_db(db)
        embed = discord.Embed(title="🎰 Machine à sous", description=desc_res + f"\n\n🎉 **GAGNÉ !** +{winnings} coins (x{multiplier}){msg_streak}", color=0x00ff00)
    else:
        db[uid] -= amount
        db[streak_key] = 0 # Reset streak
        save_db(db)
        embed = discord.Embed(title="🎰 Machine à sous", description=desc_res + "\n\n❌ Perdu... Série brisée.", color=0xff0000)

    await ctx.send(embed=embed)

# --- MORPION AVEC ACCEPTATION ---
class DuelView(discord.ui.View):
    def __init__(self, challenger, opponent, amount):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.accepted = False

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("Ce n'est pas ton défi !", ephemeral=True)
        
        # Vérification finale des fonds de l'adversaire
        db = load_db()
        op_bal = db.get(str(self.opponent.id), 0)
        ch_bal = db.get(str(self.challenger.id), 0) # On revérifie au cas où

        if op_bal < self.amount:
            return await interaction.response.send_message("❌ Tu n'as pas assez d'argent pour accepter !", ephemeral=True)
        if ch_bal < self.amount:
            return await interaction.response.send_message(f"❌ {self.challenger.display_name} n'a plus assez d'argent !", ephemeral=True)

        # Prélèvement des mises
        if self.amount > 0:
            db[str(self.challenger.id)] -= self.amount
            db[str(self.opponent.id)] -= self.amount
            save_db(db)

        self.accepted = True
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content=f"✅ **Défi accepté !** Mise : {self.amount} chacun.", view=None)
        
        # Lancement du jeu
        await interaction.channel.send(
            f"🎮 {self.challenger.mention} vs {self.opponent.mention} - C'est parti !", 
            view=TicTacToeView(self.challenger, self.opponent, self.amount)
        )
        self.stop()

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("Ce n'est pas ton défi !", ephemeral=True)
        
        self.accepted = False
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content=f"❌ **Défi refusé** par {self.opponent.display_name}.", view=self)
        self.stop()

class TicTacToeButton(discord.ui.Button["TicTacToeView"]):
    def __init__(self, x, y): super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y); self.x, self.y = x, y
    async def callback(self, interaction):
        view = self.view
        if interaction.user != view.current_player: return await interaction.response.send_message("Pas ton tour !", ephemeral=True)
        if self.label != "⬜": return
        self.label = "❌" if view.current_player == view.p1 else "⭕"
        self.style = discord.ButtonStyle.danger if view.current_player == view.p1 else discord.ButtonStyle.success
        view.board[self.y][self.x] = 1 if view.current_player == view.p1 else 2
        next_p = view.p2 if view.current_player == view.p1 else view.p1
        view.current_player = next_p
        
        if view.check_winner():
            winner = interaction.user
            pot = view.amount * 2
            msg = f"🏆 **{winner.display_name} gagne !**"
            if view.amount > 0:
                view.db = load_db()
                view.db[str(winner.id)] = view.db.get(str(winner.id), 0) + pot
                save_db(view.db)
                msg += f"\n💰 Il remporte **{pot} coins** !"
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=msg, view=view)
            view.stop()
        elif view.is_full():
            msg = "🤝 Match nul !"
            if view.amount > 0:
                view.db = load_db()
                view.db[str(view.p1.id)] += view.amount
                view.db[str(view.p2.id)] += view.amount
                save_db(view.db)
                msg += " (Mises remboursées)"
            await interaction.response.edit_message(content=msg, view=view)
            view.stop()
        else: await interaction.response.edit_message(content=f"Tour de : {view.current_player.mention}", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2, amount=0):
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
    if member.bot or member == ctx.author:
        return await ctx.send("❌ Impossible de jouer contre un bot ou soi-même.")
    
    db = load_db()
    balance = db.get(str(ctx.author.id), 0)
    amount = parse_amount(amount_str, balance)
    
    # Vérification fonds du lanceur du défi
    if amount > 0:
        if balance < amount:
            return await ctx.send("❌ Tu n'as pas assez d'argent pour proposer cette mise.")
        
        # On ne retire pas l'argent tout de suite, on attend l'acceptation
        msg = await ctx.send(f"⚔️ {member.mention}, **{ctx.author.display_name}** te défie au Morpion pour **{amount} coins** !\nAccepte pour jouer.", view=DuelView(ctx.author, member, amount))
    else:
        # Pas de mise, on demande quand même acceptation pour la forme (ou on lance direct si tu préfères, ici je demande)
        msg = await ctx.send(f"⚔️ {member.mention}, **{ctx.author.display_name}** te défie au Morpion (Amical) !", view=DuelView(ctx.author, member, 0))

# --- BLACKJACK & ROULETTE & ECO ---
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=60)
        self.author_id, self.amount, self.db = author_id, amount, db
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        self.player_hand = [self.draw(), self.draw()]; self.dealer_hand = [self.draw(), self.draw()]
    def draw(self): return random.choice(self.deck)
    def score(self, hand):
        s = sum(hand); n_aces = hand.count(11)
        while s > 21 and n_aces > 0: s -= 10; n_aces -= 1
        return s
    async def end_game(self, interaction, result_msg, win_mult):
        for child in self.children: child.disabled = True
        uid = str(self.author_id)
        if win_mult > 0: self.db[uid] = self.db.get(uid, 0) + int(self.amount * win_mult); save_db(self.db); color = 0x00ff00
        else: color = 0xff0000
        embed = discord.Embed(title="🃏 Blackjack", description=result_msg, color=color)
        embed.add_field(name="Toi", value=f"{self.player_hand} ({self.score(self.player_hand)})"); embed.add_field(name="Croupier", value=f"{self.dealer_hand} ({self.score(self.dealer_hand)})")
        await interaction.response.edit_message(embed=embed, view=self)
    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        if self.score(self.player_hand) > 21: await self.end_game(interaction, "💥 Sauté !", 0)
        else:
            embed = discord.Embed(title="🃏 Blackjack", color=0x4b41e6); embed.add_field(name="Toi", value=f"{self.player_hand} ({self.score(self.player_hand)})"); embed.add_field(name="Croupier", value=f"[{self.dealer_hand[0]}, ?]")
            await interaction.response.edit_message(embed=embed, view=self)
    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        while self.score(self.dealer_hand) < 17: self.dealer_hand.append(self.draw())
        ps, ds = self.score(self.player_hand), self.score(self.dealer_hand)
        if ds > 21: await self.end_game(interaction, "🎉 Croupier saute !", 2)
        elif ps > ds: await self.end_game(interaction, "🎉 Gagné !", 2)
        elif ps == ds: await self.end_game(interaction, "🤝 Égalité.", 1)
        else: await self.end_game(interaction, "❌ Perdu.", 0)

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    balance = db.get(uid, 0)
    amount = parse_amount(amount_str, balance)
    
    if amount <= 0 or balance < amount: return await ctx.send("❌ Pas assez d'argent.")
    db[uid] -= amount; save_db(db); await ctx.send(embed=discord.Embed(title="🃏 Blackjack", description=f"Mise: {amount}"), view=BlackjackView(ctx.author.id, amount, db))

@bot.command()
async def roulette(ctx, amount_str: str, choice: str):
    choice = choice.lower(); db = load_db(); uid = str(ctx.author.id)
    balance = db.get(uid, 0)
    amount = parse_amount(amount_str, balance)

    if choice not in ["noir", "rouge"] or balance < amount or amount <= 0: return await ctx.send("❌ Erreur saisie ou fonds.")
    res = random.choice(["rouge", "noir"])
    if choice == res: db[uid] += amount; save_db(db); await ctx.send(f"🎰 **{res.upper()}** ! Tu gagnes {amount*2} !")
    else: db[uid] -= amount; save_db(db); await ctx.send(f"🎰 **{res.upper()}** ! Perdu {amount}.")

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_last_daily"
    if time.time() - db.get(key, 0) < 43200: return await ctx.send("⏳ Reviens plus tard.")
    gain = random.randint(500, 1000); db[uid] = db.get(uid, 0) + gain; db[key] = time.time(); save_db(db); await ctx.send(f"🎁 +{gain} coins !")

@bot.command()
async def work(ctx):
    db = load_db(); gain = random.randint(100, 350); db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain; save_db(db); await ctx.send(f"🔨 +{gain} coins !")

@bot.command()
async def rob(ctx, member: discord.Member):
    if member == ctx.author: return
    db = load_db(); v_bal = db.get(str(member.id), 0)
    if v_bal < 200: return await ctx.send("❌ Trop pauvre.")
    if random.choice([True, False]):
        stolen = random.randint(int(v_bal * 0.05), int(v_bal * 0.20)); db[str(ctx.author.id)] += stolen; db[str(member.id)] -= stolen; save_db(db); await ctx.send(f"🥷 Volé : {stolen} !")
    else: db[str(ctx.author.id)] = max(0, db.get(str(ctx.author.id), 0) - 100); save_db(db); await ctx.send("👮 Amende -100.")

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    db = load_db()
    await ctx.send(f"💰 **{target.display_name}** possède **{db.get(str(target.id), 0)} coins**")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Boutique", color=0x4b41e6)
    for k, v in SHOP_ITEMS.items(): embed.add_field(name=k.upper(), value=f"💰 {v}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item: str):
    db = load_db(); uid = str(ctx.author.id); item = item.lower().strip()
    if item not in SHOP_ITEMS: return await ctx.send("❌ Inconnu.")
    price = SHOP_ITEMS[item]; role = discord.utils.find(lambda r: r.name.lower() == item, ctx.guild.roles)
    if not role or db.get(uid, 0) < price: return await ctx.send("❌ Erreur (Rôle ou Argent).")
    try: db[uid] -= price; save_db(db); await ctx.author.add_roles(role); await ctx.send(f"🎉 Acheté : **{role.name}** !")
    except: await ctx.send("❌ Permissions.")

@bot.command(name="help-slot")
async def help_slot(ctx):
    em = discord.Embed(title="🎰 Info Slot", description="7️⃣7️⃣7️⃣ = x100\n💎💎💎 = x50\nUne paire = x1.5\n\n🔥 **7 victoires de suite = Rôle HAKARI**", color=0xFFD700); await ctx.send(embed=em)

@bot.command(name="helpme")
async def helpme(ctx):
    em = discord.Embed(title="Aide Pandora", description="Voici toutes les commandes disponibles.", color=0x4b41e6)
    em.add_field(name="🏇 Courses (Multi)", value="`!race` (Lancer lobby)\n`!bet <mise> <cheval>` (Rejoindre)\n🏅 10 victoires = Rôle **Dompteur**", inline=False)
    em.add_field(name="🎰 Casino", value="`!slot <mise/all>`\n`!blackjack <mise/all>`\n`!morpion @joueur <mise/all>`\n`!roulette <mise/all> <couleur>`", inline=False)
    em.add_field(name="💰 Économie", value="`!bal`, `!work`, `!daily`, `!rob @joueur`, `!give @joueur <montant/all>`, `!top`", inline=False)
    em.add_field(name="🛒 Shop", value="`!shop`, `!buy <item>`", inline=False)
    await ctx.send(embed=em)

# --- 7. RUN ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown): await ctx.send(f"⏳ Cooldown : {int(error.retry_after)}s.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions): await ctx.send("❌ Tu n'as pas la permission.", delete_after=5)

keep_alive()
bot.run(os.environ.get('TOKEN'))
