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
def home(): return "Pandora Casino V5 Ultimate est en ligne !"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. BASE DE DONNÉES ---
DB_FILE = "database.json"
TAX_RATE = 0.05 # 5% de taxe sur les échanges entre joueurs

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

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

# --- 3. CONFIGURATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- 4. CLASSES DE JEUX ---

# === BLACKJACK AMÉLIORÉ ===
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount, db):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.amount = amount
        self.db = db
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A'] * 4
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]
        self.ended = False

    def draw(self):
        return random.choice(self.deck)

    def calculate_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            if isinstance(card, int): score += card
            elif card in ['J', 'Q', 'K']: score += 10
            elif card == 'A': 
                score += 11
                aces += 1
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        return score

    def format_hand(self, hand, hide_second=False):
        txt = ""
        for i, card in enumerate(hand):
            if hide_second and i == 1: txt += "[🎴]"
            else: txt += f"[`{card}`] "
        return txt

    async def update_message(self, interaction, result_msg=None, color=0x4b41e6, hide_dealer=True):
        p_score = self.calculate_score(self.player_hand)
        d_score = self.calculate_score(self.dealer_hand)
        
        embed = discord.Embed(title="🃏 BlackJack", color=color)
        embed.add_field(name=f"👤 Ta main ({p_score})", value=self.format_hand(self.player_hand), inline=False)
        
        if hide_dealer:
            embed.add_field(name="🎩 Croupier", value=self.format_hand(self.dealer_hand, hide_second=True), inline=False)
        else:
            embed.add_field(name=f"🎩 Croupier ({d_score})", value=self.format_hand(self.dealer_hand, hide_second=False), inline=False)

        if result_msg:
            embed.add_field(name="Résultat", value=result_msg, inline=False)
            embed.set_footer(text=f"Mise : {self.amount} coins")

        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Tirer (Hit)", style=discord.ButtonStyle.primary, emoji="➕")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        score = self.calculate_score(self.player_hand)
        
        if score > 21:
            self.ended = True
            for child in self.children: child.disabled = True
            # Perdu : L'argent est déjà retiré au lancement, on ne fait rien
            await self.update_message(interaction, "💥 **BUST !** Tu as dépassé 21. Perdu.", 0xff0000, hide_dealer=False)
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Rester (Stand)", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.ended = True
        for child in self.children: child.disabled = True
        
        # Le croupier joue
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw())
        
        p_score = self.calculate_score(self.player_hand)
        d_score = self.calculate_score(self.dealer_hand)
        
        uid = str(self.author_id)
        
        if d_score > 21:
            msg = "🎉 Le Croupier a sauté ! **Tu gagnes !**"
            win = True
        elif p_score > d_score:
            msg = "🎉 Ton score est meilleur ! **Tu gagnes !**"
            win = True
        elif p_score == d_score:
            msg = "🤝 Égalité ! Mise remboursée."
            self.db[uid] = self.db.get(uid, 0) + self.amount
            save_db(self.db)
            await self.update_message(interaction, msg, 0xFFA500, hide_dealer=False)
            return
        else:
            msg = f"❌ Le Croupier a {d_score}. **Tu perds.**"
            win = False

        if win:
            gain = self.amount * 2
            self.db[uid] = self.db.get(uid, 0) + gain
            save_db(self.db)
            color = 0x00ff00
            msg += f"\n💰 +{gain} coins"
        else:
            color = 0xff0000

        await self.update_message(interaction, msg, color, hide_dealer=False)

# === MORPION (TICTACTOE) CORRIGÉ ===
class MorpionGame(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.amount = amount
        self.turn = p1
        self.board = [0] * 9
        # Ajout des boutons 3x3
        for i in range(9):
            self.add_item(MorpionButton(i))

    async def game_over(self, interaction, winner=None):
        for child in self.children: child.disabled = True
        db = load_db()
        
        if winner:
            pot = self.amount * 2
            db[str(winner.id)] = db.get(str(winner.id), 0) + pot
            save_db(db)
            embed = discord.Embed(title="🎮 Morpion - Fin", description=f"🏆 **{winner.mention} remporte la victoire !**\n💰 Gain : **{pot} coins**", color=0x00ff00)
        else:
            # Match nul = Remboursement
            db[str(self.p1.id)] = db.get(str(self.p1.id), 0) + self.amount
            db[str(self.p2.id)] = db.get(str(self.p2.id), 0) + self.amount
            save_db(db)
            embed = discord.Embed(title="🎮 Morpion - Fin", description="🤝 **Match Nul !**\nVos mises ont été remboursées.", color=0xFFA500)
            
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

class MorpionButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(style=discord.ButtonStyle.secondary, label="➖", row=index//3)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: MorpionGame = self.view
        if interaction.user != view.turn:
            return await interaction.response.send_message("Ce n'est pas ton tour !", ephemeral=True)
        
        # Marquer la case
        symbol = "❌" if view.turn == view.p1 else "⭕"
        self.style = discord.ButtonStyle.danger if view.turn == view.p1 else discord.ButtonStyle.success
        self.label = symbol
        self.disabled = True
        view.board[self.index] = 1 if view.turn == view.p1 else 2
        
        # Vérifier victoire
        b = view.board
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for x,y,z in wins:
            if b[x] == b[y] == b[z] != 0:
                return await view.game_over(interaction, view.turn)
        
        if 0 not in b: # Plein
            return await view.game_over(interaction, None)

        # Changer tour
        view.turn = view.p2 if view.turn == view.p1 else view.p1
        await interaction.response.edit_message(content=f"Au tour de {view.turn.mention}", view=view)

class MorpionInvite(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(timeout=60)
        self.p1 = p1; self.p2 = p2; self.amount = amount

    @discord.ui.button(label="Accepter le Duel", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2: return
        
        db = load_db()
        id1, id2 = str(self.p1.id), str(self.p2.id)
        if db.get(id1, 0) < self.amount or db.get(id2, 0) < self.amount:
            return await interaction.response.edit_message(content="❌ L'un des joueurs n'a plus assez d'argent.", view=None)

        # On prélève l'argent MAINTENANT
        db[id1] -= self.amount
        db[id2] -= self.amount
        save_db(db)

        await interaction.response.edit_message(content=f"🎮 **Duel lancé !** {self.p1.mention} commence.", view=MorpionGame(self.p1, self.p2, self.amount))

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2: return
        await interaction.response.edit_message(content=f"🚫 {self.p2.mention} a refusé le duel.", view=None)

# === DICE AVEC ANIMATION ===
class DiceView(discord.ui.View):
    def __init__(self, author, amount):
        super().__init__(timeout=60)
        self.author = author; self.amount = amount; self.clicked = False

    @discord.ui.button(label="🎲 Lancer !", style=discord.ButtonStyle.primary)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author or self.clicked: return
        self.clicked = True
        
        p_roll = [random.randint(1,6), random.randint(1,6)]
        b_roll = [random.randint(1,6), random.randint(1,6)]
        p_sum = sum(p_roll); b_sum = sum(b_roll)

        db = load_db(); uid = str(self.author.id)
        embed = discord.Embed(title="🎲 Résultats des Dés", color=0x4b41e6)
        embed.add_field(name="Toi", value=f"`{p_roll[0]}` + `{p_roll[1]}` = **{p_sum}**")
        embed.add_field(name="Bot", value=f"`{b_roll[0]}` + `{b_roll[1]}` = **{b_sum}**")

        if p_sum > b_sum:
            gain = self.amount * 2
            db[uid] = db.get(uid, 0) + gain
            embed.color = 0x00ff00
            embed.description = f"🎉 **VICTOIRE !** Tu remportes {gain - self.amount} coins !"
        elif p_sum < b_sum:
            embed.color = 0xff0000
            embed.description = "❌ **DÉFAITE.** Le bot gagne."
        else:
            db[uid] = db.get(uid, 0) + self.amount
            embed.color = 0xFFA500
            embed.description = "🤝 **ÉGALITÉ.** Mise remboursée."
        
        save_db(db)
        button.disabled = True
        button.label = "Terminé"
        await interaction.response.edit_message(embed=embed, view=self)

# --- 5. COMMANDES JEUX ---

@bot.command()
async def blackjack(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Tu n'as pas assez d'argent.")

    db[uid] -= amount
    save_db(db)
    
    view = BlackjackView(ctx.author.id, amount, db)
    await view.update_message(ctx) # Envoie le message initial

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str):
    if member.bot or member == ctx.author: return await ctx.send("❌ Impossible de jouer contre un bot ou toi-même.")
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Tu n'as pas assez d'argent.")
    
    embed = discord.Embed(title="⚔️ Défi Morpion", description=f"{ctx.author.mention} défie {member.mention} pour **{amount} coins** !", color=0xFFFF00)
    await ctx.send(member.mention, embed=embed, view=MorpionInvite(ctx.author, member, amount))

@bot.command()
async def dice(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")

    db[uid] -= amount
    save_db(db)
    
    embed = discord.Embed(title="🎲 Dice", description=f"Mise : **{amount} coins**\nClique sur le bouton pour lancer.", color=0x4b41e6)
    await ctx.send(embed=embed, view=DiceView(ctx.author, amount))

@bot.command()
async def slot(ctx, amount_str: str):
    db = load_db(); uid = str(ctx.author.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Pas assez d'argent.")
    
    symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
    weights = [30, 25, 20, 15, 8, 2]
    res = random.choices(symbols, weights=weights, k=3)
    
    mult = 0
    if res[0] == res[1] == res[2]:
        mult = {"7️⃣":100, "💎":50, "🔔":20, "🍇":10, "🍋":5, "🍒":3}[res[0]]
    elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]: mult = 1.5

    embed = discord.Embed(title="🎰 Machine à Sous", color=0x4b41e6)
    desc = f"**»** ┃ {res[0]} ┃ {res[1]} ┃ {res[2]} ┃ **«**\n\n"
    
    if mult > 0:
        gain = int(amount * mult)
        db[uid] += (gain - amount)
        embed.color = 0x00ff00
        desc += f"🎉 **GAGNÉ !** x{mult} -> **+{gain} coins**"
    else:
        db[uid] -= amount
        embed.color = 0xff0000
        desc += f"❌ **PERDU** -{amount} coins"
    
    save_db(db)
    embed.description = desc
    await ctx.send(embed=embed)

# --- 6. ÉCONOMIE & ADMIN ---

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(100, 500)
    db = load_db()
    db[str(ctx.author.id)] = db.get(str(ctx.author.id), 0) + gain
    save_db(db)
    await ctx.send(f"🔨 Tu as travaillé et gagné **{gain} coins** !")

@bot.command()
async def daily(ctx):
    db = load_db(); uid = str(ctx.author.id); key = f"{uid}_daily"
    if time.time() - db.get(key, 0) < 43200:
        remaining = 43200 - (time.time() - db.get(key, 0))
        h, m = divmod(remaining, 3600)
        return await ctx.send(f"⏳ Reviens dans {int(h)}h {int(m//60)}m.")
    
    gain = random.randint(1000, 5000)
    db[uid] = db.get(uid, 0) + gain
    db[key] = time.time()
    save_db(db)
    await ctx.send(f"🎁 **Bonus Quotidien !** Tu reçois **{gain} coins** !")

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member == ctx.author: return
    db = load_db(); uid = str(ctx.author.id); tid = str(member.id)
    amount = parse_amount(amount_str, db.get(uid, 0))
    
    if amount <= 0 or db.get(uid, 0) < amount: return await ctx.send("❌ Fonds insuffisants.")
    
    tax = int(amount * TAX_RATE)
    final = amount - tax
    
    db[uid] -= amount
    db[tid] = db.get(tid, 0) + final
    save_db(db)
    
    embed = discord.Embed(title="💸 Transfert", color=0x00ff00)
    embed.add_field(name="Envoyé", value=str(amount))
    embed.add_field(name="Taxe (5%)", value=str(tax))
    embed.add_field(name="Reçu", value=str(final))
    await ctx.send(f"{ctx.author.mention} a payé {member.mention}", embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount_str: str):
    """Retire de l'argent à un joueur (Admin)"""
    db = load_db(); uid = str(member.id)
    amount = parse_amount(amount_str, db.get(uid, 0)) # On permet "all" aussi
    
    current = db.get(uid, 0)
    if amount > current: amount = current # On ne peut pas taxer plus qu'il n'a
    
    db[uid] = current - amount
    save_db(db)
    
    await ctx.send(f"👮 **TAXE** : L'administrateur a saisi **{amount} coins** à {member.mention}.\nNouveau solde : {db[uid]}")

@bot.command(name="admin-give")
@commands.has_permissions(administrator=True)
async def admin_give(ctx, member: discord.Member, amount: int):
    db = load_db(); uid = str(member.id)
    db[uid] = db.get(uid, 0) + amount
    save_db(db)
    await ctx.send(f"👑 **Don Admin** : +{amount} coins pour {member.mention}")

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member or ctx.author
    db = load_db()
    embed = discord.Embed(title="💰 Banque", description=f"Solde de {target.mention} : **{db.get(str(target.id), 0)} coins**", color=0xFFD700)
    await ctx.send(embed=embed)

@bot.command()
async def helpme(ctx):
    e = discord.Embed(title="Aide Pandora V5", color=0x4b41e6)
    e.add_field(name="🎮 Jeux", value="`!blackjack`, `!morpion`, `!dice`, `!slot`\n*Supportent 'all' comme mise*", inline=False)
    e.add_field(name="💰 Argent", value="`!work` (10min), `!daily` (12h), `!give`, `!bal`", inline=False)
    e.add_field(name="👮 Admin", value="`!tax @user <montant>`, `!admin-give`", inline=False)
    await ctx.send(embed=e)

# --- 7. GESTION DES ERREURS & COOLDOWN (FIX) ---
@bot.event
async def on_command_error(ctx, error):
    # Fix: Affiche le message à chaque fois
    if isinstance(error, commands.CommandOnCooldown):
        # Convertir le temps en format lisible
        m, s = divmod(error.retry_after, 60)
        h, m = divmod(m, 60)
        
        if h > 0: time_fmt = f"{int(h)}h {int(m)}m {int(s)}s"
        elif m > 0: time_fmt = f"{int(m)}m {int(s)}s"
        else: time_fmt = f"{int(s)}s"
        
        emb = discord.Embed(title="⏳ Doucement !", description=f"Tu dois attendre encore **{time_fmt}** avant de refaire cette commande.", color=0xFFA500)
        await ctx.send(embed=emb, delete_after=10)
        
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Tu n'as pas la permission.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Commande incomplète. Vérifie la syntaxe.", delete_after=5)
    else:
        # Pour le debug, on affiche les autres erreurs dans la console uniquement
        print(f"Erreur : {error}")

keep_alive()
bot.run(os.environ.get('TOKEN'))
