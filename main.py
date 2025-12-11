import discord
from discord.ext import commands
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ Fichier .env manquant ou token absent.")

# Intents requis (à activer dans le portail)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
os.makedirs("data", exist_ok=True)

async def init_db():
    async with aiosqlite.connect("data/ciel.db") as db:
        # Welcome
        await db.execute("""CREATE TABLE IF NOT EXISTS welcome (
            guild_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            gif_url TEXT,
            channel_id INTEGER
        )""")
        # Tickets
        await db.execute("""CREATE TABLE IF NOT EXISTS ticket_categories (
            name TEXT PRIMARY KEY,
            emoji TEXT,
            description TEXT,
            target_channel_id INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            category TEXT
        )""")
        # Bypass
        await db.execute("""CREATE TABLE IF NOT EXISTS bypass (
            user_id INTEGER,
            channel_id INTEGER,
            granted_by INTEGER,
            PRIMARY KEY (user_id, channel_id)
        )""")
        # Logs
        await db.execute("""CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            type TEXT,
            data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        # Sécurité
        await db.execute("""CREATE TABLE IF NOT EXISTS security (
            guild_id INTEGER PRIMARY KEY,
            anti_spam_channels TEXT,
            anti_invite_channels TEXT
        )""")
        await db.commit()

async def load_cogs():
    for f in os.listdir("cogs"):
        if f.endswith(".py") and f != "__init__.py":
            await bot.load_extension(f"cogs.{f[:-3]}")

@bot.event
async def on_ready():
    print("🔄 Synchronisation des commandes slash...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commandes synchronisées.")
    except Exception as e:
        print(f"❌ Erreur : {e}")
    print(f"🟢 CIEL OS v3.14 — Connecté en tant que {bot.user}")

async def main():
    await init_db()
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())