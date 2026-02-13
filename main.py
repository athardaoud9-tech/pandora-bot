import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from flask import Flask
from threading import Thread

# --- SERVEUR POUR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Pandora Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- BOT CONFIG ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    try:
        with open("database.json", "r") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open("database.json", "w") as f: json.dump(data, f, indent=4)

# --- COMMANDES ---

@bot.tree.command(name="daily", description="Récupère ton argent (12h)")
@app_commands.checks.cooldown(1, 43200) # Cooldown de 12h
async def daily(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    data[uid] = data.get(uid, {"balance": 0})
    data[uid]["balance"] += 500
    save_data(data)
    await interaction.response.send_message("💰 +500$ ! Reviens dans 12h.")

@bot.tree.command(name="work", description="Travaille pour gagner de l'argent")
@app_commands.checks.cooldown(1, 3600)
async def work(interaction: discord.Interaction):
    data = load_data()
    uid = str(interaction.user.id)
    gain = random.randint(100, 300)
    data[uid] = data.get(uid, {"balance": 0})
    data[uid]["balance"] += gain
    save_data(data)
    await interaction.response.send_message(f"🛠️ Tu as travaillé et gagné {gain}$ !")

@bot.tree.command(name="rob", description="Voler un membre")
async def rob(interaction: discord.Interaction, membre: discord.Member):
    data = load_data()
    vilein = str(interaction.user.id)
    victime = str(membre.id)
    if victime not in data or data[victime]["balance"] < 100:
        return await interaction.response.send_message("Trop pauvre pour être volé.")
    vol = random.randint(50, 100)
    data[vilein]["balance"] += vol
    data[victime]["balance"] -= vol
    save_data(data)
    await interaction.response.send_message(f"🥷 Tu as volé {vol}$ à {membre.mention} !")

@bot.tree.command(name="taxe", description="Taxer un membre (Admin)")
@app_commands.checks.has_permissions(administrator=True)
async def taxe(interaction: discord.Interaction, membre: discord.Member, montant: int):
    data = load_data()
    uid = str(membre.id)
    if data.get(uid, {}).get("balance", 0) < montant:
        return await interaction.response.send_message("Fonds insuffisants.", ephemeral=True)
    data[uid]["balance"] -= montant
    save_data(data)
    await interaction.response.send_message(f"💸 Taxe de {montant}$ prélevée sur {membre.mention}.")

@bot.tree.command(name="morpion", description="Jouer au morpion")
async def morpion(interaction: discord.Interaction):
    await interaction.response.send_message("🎮 Le jeu de morpion arrive bientôt !")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} est prêt !")

keep_alive() # Pour éviter le "Timed out" sur Render
bot.run(os.getenv('TOKEN'))
