import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# --- CONFIGURATION DU SERVEUR WEB POUR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Pandora Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION DU BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Chargement de la base de données
def load_data():
    try:
        with open("database.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open("database.json", "w") as f:
        json.dump(data, f, indent=4)

# --- COMMANDES D'ÉCONOMIE ---

@bot.tree.command(name="daily", description="Reçois ton argent quotidien toutes les 12h")
@app_commands.checks.cooldown(1, 43200) # 43200 secondes = 12 heures
async def daily(interaction: discord.Interaction):
    data = load_data()
    user_id = str(interaction.user.id)
    
    if user_id not in data:
        data[user_id] = {"balance": 0}
    
    reward = 500
    data[user_id]["balance"] += reward
    save_data(data)
    
    await interaction.response.send_message(f"💰 Tu as reçu tes **{reward}$** quotidiens ! Reviens dans 12h.")

@bot.tree.command(name="taxe", description="Taxer un membre (Admin seulement)")
@app_commands.checks.has_permissions(administrator=True)
async def taxe(interaction: discord.Interaction, membre: discord.Member, montant: int):
    data = load_data()
    user_id = str(membre.id)
    
    if user_id not in data or data[user_id]["balance"] < montant:
        await interaction.response.send_message("Ce membre n'a pas assez d'argent pour être taxé de ce montant.", ephemeral=True)
        return
    
    data[user_id]["balance"] -= montant
    save_data(data)
    
    await interaction.response.send_message(f"💸 L'administration a prélevé une taxe de **{montant}$** à {membre.mention} !")

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# --- LANCEMENT ---
keep_alive() # Indispensable pour Render
token = os.getenv('TOKEN') # Récupère le TOKEN des variables d'environnement
bot.run(token)
