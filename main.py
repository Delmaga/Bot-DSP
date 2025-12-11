import discord
from discord.ext import commands
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv

# Chargement sécurisé du token
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ Le token Discord est manquant. Vérifie ton fichier .env !")

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Création du dossier data si absent
os.makedirs("data", exist_ok=True)

async def init_db():
    async with aiosqlite.connect("data/ciel.db") as db:
        # Table tickets
        await db.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_id INTEGER,
            category TEXT,
            guild_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Table welcome
        await db.execute("""CREATE TABLE IF NOT EXISTS welcome (
            guild_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            gif_url TEXT,
            channel_id INTEGER
        )""")
        # Table catégories de tickets
        await db.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            emoji TEXT,
            description TEXT
        )""")
        # Table bypass
        await db.execute("""CREATE TABLE IF NOT EXISTS bypass (
            user_id INTEGER,
            channel_id INTEGER,
            granted_by INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, channel_id)
        )""")
        # Logs de modération
        await db.execute("""CREATE TABLE IF NOT EXISTS moderation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            target_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            duration TEXT,
            guild_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

async def load_cogs():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    print("✅ CIEL OS v3.14 — Système opérationnel.")
    print(f"👤 Connecté en tant que : {bot.user}")
    print(f"🌐 Serveurs actifs : {len(bot.guilds)}")
    await bot.change_presence(activity=discord.Game(name="Protégeant Los Santos..."))

async def main():
    await init_db()
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())