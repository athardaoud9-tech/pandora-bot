import discord
from discord.ext import commands
import os
import time
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# --- 1. KEEP ALIVE (Pour hébergeur gratuit) ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Casino V6 est en ligne !"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. GESTION BASE DE DONNÉES (OPTIMISÉE) ---
DB_FILE = "database.json"

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
    """Ajoute ou retire de l'argent de façon sécurisée."""
    db = get_db()
    uid = str(user_id)
    new_bal = db.get(uid, 0) + amount
    db[uid] = new_bal
    save_db(db)
    return new_bal

def parse_amount(amount_str, user_id):
    """Gère les nombres et le mot 'all'."""
    bal = get_balance(user_id)
    if str(amount_str).lower() in ["all", "tout"]:
        return int(bal)
    try:
        val = int(amount_str)
        return val if val > 0 else 0
    except ValueError:
        return 0

# --- 3. CONFIGURATION BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- 4. CLASSES DE JEUX (VIEWS) ---

# === BLACKJACK ===
class BlackjackView(discord.ui.View):
    def __init__(self, author_id, amount):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.amount = amount
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A'] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.draw(), self.draw()]
        self.dealer_hand = [self.draw(), self.draw()]
        self.finished = False

    def draw(self): return self.deck.pop()

    def calculate_score(self, hand):
        score = 0; aces = 0
        for card in hand:
            if isinstance(card, int): score += card
            elif card in ['J', 'Q', 'K']: score += 10
            elif card == 'A': score += 11; aces += 1
        while score > 21 and aces: score -= 10; aces -= 1
        return score

    def get_embed(self, hide_dealer=True, result_text=None, color=0x4b41e6):
        p_score = self.calculate_score(self.player_hand)
        d_score = self.calculate_score(self.dealer_hand)
        
        desc = f"Mise : **{self.amount} coins**\n"
        if result_text: desc += f"\n{result_text}\n"

        e = discord.Embed(title="🃏 Blackjack", description=desc, color=color)
        e.add_field(name=f"👤 Toi ({p_score})", value=f"`{self.player_hand}`", inline=False)
        
        if hide_dealer:
            e.add_field(name="🎩 Croupier", value=f"[`{self.dealer_hand[0]}`, `?`]", inline=False)
        else:
            e.add_field(name=f"🎩 Croupier ({d_score})", value=f"`{self.dealer_hand}`", inline=False)
        return e

    async def end_game(self, interaction, result, win_multiplier):
        self.finished = True
        for child in self.children: child.disabled = True
        
        if win_multiplier > 0:
            profit = int(self.amount * win_multiplier)
            update_balance(self.author_id, profit) # Rembourse mise + gain
            color = 0x00ff00
            msg = f"🎉 **{result}** (+{profit - self.amount} net)"
        elif win_multiplier == 1: # Égalité (Push)
            update_balance(self.author_id, self.amount)
            color = 0xFFA500
            msg = f"🤝 **{result}** (Remboursé)"
        else:
            color = 0xff0000
            msg = f"❌ **{result}** (-{self.amount})"

        await interaction.response.edit_message(embed=self.get_embed(hide_dealer=False, result_text=msg, color=color), view=self)
        self.stop()

    @discord.ui.button(label="Tirer", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        self.player_hand.append(self.draw())
        if self.calculate_score(self.player_hand) > 21:
            await self.end_game(interaction, "BUST ! Tu as sauté.", 0)
        else:
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Rester", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw())
            
        p = self.calculate_score(self.player_hand)
        d = self.calculate_score(self.dealer_hand)
        
        if d > 21: await self.end_game(interaction, "Le Croupier saute ! Tu gagnes.", 2)
        elif p > d: await self.end_game(interaction, "Tu bats le Croupier !", 2)
        elif p == d: await self.end_game(interaction, "Égalité.", 1) # 1 = Remboursement exact
        else: await self.end_game(interaction, "Le Croupier gagne.", 0)

# === MORPION (TIC TAC TOE) ===
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y)
        self.x = x; self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current_turn: return
        
        state = 1 if view.current_turn == view.p1 else 2
        label = "❌" if state == 1 else "⭕"
        style = discord.ButtonStyle.danger if state == 1 else discord.ButtonStyle.success
        
        self.style = style; self.label = label; self.disabled = True
        view.board[self.y][self.x] = state
        
        winner = view.check_winner()
        if winner:
            view.game_over = True
            pot = view.amount * 2
            update_balance(winner.id, pot)
            for child in view.children: child.disabled = True
            await interaction.response.edit_message(content=f"🏆 **{winner.mention} remporte {pot} coins !**", view=view)
            view.stop()
        elif all(cell != 0 for row in view.board for cell in row):
            view.game_over = True
            update_balance(view.p1.id, view.amount)
            update_balance(view.p2.id, view.amount)
            await interaction.response.edit_message(content="🤝 **Match Nul !** Mises remboursées.", view=view)
            view.stop()
        else:
            view.current_turn = view.p2 if view.current_turn == view.p1 else view.p1
            await interaction.response.edit_message(content=f"Au tour de : {view.current_turn.mention}", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(timeout=60)
        self.p1 = p1; self.p2 = p2; self.amount = amount
        self.current_turn = p1; self.board = [[0]*3 for _ in range(3)]
        for y in range(3):
            for x in range(3): self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        b = self.board
        # Lignes, Colonnes, Diagonales
        lines = b + [[b[r][c] for r in range(3)] for c in range(3)] + [[b[i][i] for i in range(3)], [b[i][2-i] for i in range(3)]]
        for line in lines:
            if line[0] == line[1] == line[2] and line[0] != 0:
                return self.p1 if line[0] == 1 else self.p2
        return None

class DuelInvite(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(timeout=60)
        self.p1 = p1; self.p2 = p2; self.amount = amount

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2: return
        # Vérification finale des fonds
        if get_balance(self.p1.id) < self.amount or get_balance(self.p2.id) < self.amount:
            return await interaction.response.send_message("❌ Un des joueurs n'a plus assez d'argent !", ephemeral=True)
        
        # Prélèvement
        update_balance(self.p1.id, -self.amount)
        update_balance(self.p2.id, -self.amount)
        
        await interaction.response.edit_message(content=f"🎮 **Duel lancé !** {self.p1.mention} commence.", view=TicTacToeView(self.p1, self.p2, self.amount))

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2: return
        await interaction.response.edit_message(content=f"🚫 Duel refusé par {self.p2.mention}.", view=None)

# === DICE ===
class DiceView(discord.ui.View):
    def __init__(self, author_id, amount):
        super().__init__(timeout=60)
        self.author_id = author_id; self.amount = amount

    @discord.ui.button(label="Lancer les dés", style=discord.ButtonStyle.blurple, emoji="🎲")
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return
        
        user_score = random.randint(2, 12)
        bot_score = random.randint(2, 12)
        
        embed = discord.Embed(title="🎲 Dés", color=0x4b41e6)
        embed.add_field(name="Toi", value=str(user_score))
        embed.add_field(name="Bot", value=str(bot_score))
        
        if user_score > bot_score:
            profit = self.amount * 2
            update_balance(self.author_id, profit) # Rembourse mise + gain (profit net = amount)
            embed.color = 0x00ff00
            embed.description = f"🎉 **Gagné !** +{self.amount} coins"
        elif user_score < bot_score:
            embed.color = 0xff0000
            embed.description = f"❌ **Perdu...** -{self.amount} coins"
        else:
            update_balance(self.author_id, self.amount) # Rembourse mise
            embed.color = 0xFFA500
            embed.description = "🤝 **Égalité.** Mise remboursée."
            
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

# --- 5. COMMANDES DU BOT ---

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    await bot.change_presence(activity=discord.Game(name="!helpme | Casino"))

@bot.command()
async def blackjack(ctx, amount_str: str):
    uid = ctx.author.id
    amount = parse_amount(amount_str, uid)
    if amount <= 0: return await ctx.send("❌ Montant invalide ou fonds insuffisants.")
    
    # Prélèvement immédiat pour éviter la triche (quitter la partie)
    update_balance(uid, -amount)
    
    view = BlackjackView(uid, amount)
    await ctx.send(embed=view.get_embed(), view=view)

@bot.command()
async def morpion(ctx, member: discord.Member, amount_str: str):
    if member.bot or member.id == ctx.author.id: return await ctx.send("❌ Adversaire invalide.")
    amount = parse_amount(amount_str, ctx.author.id)
    if amount <= 0: return await ctx.send("❌ Tu n'as pas assez d'argent.")
    
    # On ne prélève PAS tout de suite, seulement si accepté
    embed = discord.Embed(description=f"⚔️ {ctx.author.mention} défie {member.mention} pour **{amount} coins** !", color=0xFFFF00)
    await ctx.send(member.mention, embed=embed, view=DuelInvite(ctx.author, member, amount))

@bot.command()
async def dice(ctx, amount_str: str):
    uid = ctx.author.id
    amount = parse_amount(amount_str, uid)
    if amount <= 0: return await ctx.send("❌ Fonds insuffisants.")
    
    update_balance(uid, -amount)
    embed = discord.Embed(description=f"Mise : **{amount} coins**. Clique pour lancer !", color=0x4b41e6)
    await ctx.send(embed=embed, view=DiceView(uid, amount))

@bot.command()
async def slot(ctx, amount_str: str):
    uid = ctx.author.id
    amount = parse_amount(amount_str, uid)
    if amount <= 0: return await ctx.send("❌ Fonds insuffisants.")
    
    update_balance(uid, -amount)
    
    # Logique Slots
    symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
    weights = [40, 30, 20, 10, 5, 2] # Probabilités
    res = random.choices(symbols, weights=weights, k=3)
    
    mult = 0
    if res[0] == res[1] == res[2]:
        if res[0] == "7️⃣": mult = 50
        elif res[0] == "💎": mult = 20
        elif res[0] == "🔔": mult = 10
        else: mult = 5
    elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
        mult = 1.5
        
    embed = discord.Embed(title="🎰 Machine à Sous", color=0x4b41e6)
    embed.description = f"**» ┃ {res[0]} ┃ {res[1]} ┃ {res[2]} ┃ «**\n\n"
    
    if mult > 0:
        gain = int(amount * mult)
        update_balance(uid, gain) # On rend la mise + gain partiel si 1.5, ou gros gain
        # Note: ici gain inclut le remboursement de la mise si on veut être strict, ou alors c'est du bonus. 
        # Pour simplifier : Si mult 1.5 et mise 100 -> gain 150. Profit 50.
        embed.color = 0x00ff00
        embed.description += f"🎉 **GAGNÉ !** x{mult} (+{gain - amount} net)"
    else:
        embed.color = 0xff0000
        embed.description += f"❌ **PERDU** (-{amount})"
        
    await ctx.send(embed=embed)

# --- COMMANDES ECO ---

@bot.command()
async def bal(ctx, member: discord.Member = None):
    target = member or ctx.author
    b = get_balance(target.id)
    await ctx.send(embed=discord.Embed(description=f"💰 **{target.display_name}** possède **{b} coins**.", color=0xFFD700))

@bot.command()
@commands.cooldown(1, 600, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(100, 400)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🔨 Tu as travaillé et gagné **{gain} coins**.")

@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id)
    db = get_db()
    last = db.get(f"{uid}_daily", 0)
    if time.time() - last < 43200: # 12h
        return await ctx.send(f"⏳ Reviens plus tard.")
    
    gain = random.randint(1000, 3000)
    update_balance(uid, gain)
    db = get_db() # Reload pour être sûr
    db[f"{uid}_daily"] = time.time()
    save_db(db)
    await ctx.send(f"🎁 **Daily** : Tu as reçu **{gain} coins** !")

@bot.command()
async def give(ctx, member: discord.Member, amount_str: str):
    if member.bot or member == ctx.author: return
    sender_id = ctx.author.id
    amount = parse_amount(amount_str, sender_id)
    
    if amount <= 0: return await ctx.send("❌ Pas assez d'argent.")
    
    tax = int(amount * 0.05)
    final = amount - tax
    
    update_balance(sender_id, -amount)
    update_balance(member.id, final)
    
    await ctx.send(f"💸 Envoi de **{amount}** (Taxe: {tax}) -> **{final}** reçus par {member.mention}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def tax(ctx, member: discord.Member, amount_str: str):
    amount = parse_amount(amount_str, member.id)
    if amount <= 0: return await ctx.send("❌ Montant invalide.")
    update_balance(member.id, -amount)
    await ctx.send(f"👮 **Taxe** : -{amount} pour {member.mention}.")

@bot.command(name="helpme")
async def helpme(ctx):
    e = discord.Embed(title="Aide Casino", color=0x4b41e6)
    e.add_field(name="Jeux", value="`!blackjack`, `!morpion`, `!dice`, `!slot`\n*Mise 'all' acceptée*", inline=False)
    e.add_field(name="Argent", value="`!work` (10m), `!daily` (12h), `!give`, `!bal`", inline=False)
    await ctx.send(embed=e)

# --- GESTION ERREURS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        h, m = divmod(m, 60)
        await ctx.send(f"⏳ Attends encore **{int(h)}h {int(m)}m {int(s)}s**.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Commande incomplète.", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(error)

keep_alive()
bot.run(os.environ.get('TOKEN'))
