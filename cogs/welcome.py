import discord
from discord.ext import commands
import aiosqlite
import os

# Créer le dossier data
os.makedirs("data", exist_ok=True)
DB_PATH = "data/welcome.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT,
                gif_url TEXT,
                channel_id INTEGER
            )
        """)
        await db.commit()

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(init_db())

    @commands.hybrid_command(name="welcome")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx, titre: str, description: str, gif_url: str, salon: discord.TextChannel):
        """Configurer le message de bienvenue.
        Exemple : /welcome "Bienvenue en Ville {member}" "Bienvenue dans ce somptueux serveur..." https://lien.gif #bienvenue
        """
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO welcome_config (guild_id, title, description, gif_url, channel_id) VALUES (?, ?, ?, ?, ?)",
                (ctx.guild.id, titre, description, gif_url, salon.id)
            )
            await db.commit()
        await ctx.send(f"✅ Bienvenue configuré dans {salon.mention} !")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT title, description, gif_url, channel_id FROM welcome_config WHERE guild_id = ?",
                (member.guild.id,)
            )
            row = await cursor.fetchone()
        
        if not row:
            return

        title, desc, gif_url, channel_id = row
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        # Remplacer {member} par la mention
        final_title = title.replace("{member}", member.mention)
        final_desc = desc.replace("{member}", member.mention)

        embed = discord.Embed(
            title=final_title,
            description=final_desc,
            color=0x00f5d4
        )
        embed.set_image(url=gif_url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Bienvenue sur le serveur • GTA RP")

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))