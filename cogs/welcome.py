import discord
from discord.ext import commands
import aiosqlite
import asyncio

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(fallback="setup")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        await ctx.send("Utilisez `/welcome set`, `/welcome test`, ou `/welcome salon`.")

    @welcome.command(name="set")
    async def set_welcome(self, ctx, title: str, description: str, gif_url: str):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO welcome (guild_id, title, description, gif_url, channel_id) VALUES (?, ?, ?, ?, ?)",
                (ctx.guild.id, title, description, gif_url, None)
            )
            await db.commit()
        await ctx.send("✅ Message de bienvenue configuré !")

    @welcome.command(name="test")
    async def test_welcome(self, ctx):
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT title, description, gif_url FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Aucun message de bienvenue configuré.")
        title, desc, gif = row
        msg = await ctx.send("```\n[CIEL OS] Authentification en cours...\n```")
        await asyncio.sleep(1)
        await msg.edit(content="```\n[CIEL OS] Scan du profil RP... OK\n```")
        await asyncio.sleep(1)
        await msg.edit(content="```\n[CIEL OS] Attribution au district...\\n[██████████] 100%\\n```")
        await asyncio.sleep(1)
        await msg.delete()
        embed = discord.Embed(title=title, description=desc, color=0x00f5d4)
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @welcome.command(name="salon")
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "UPDATE welcome SET channel_id = ? WHERE guild_id = ?",
                (channel.id, ctx.guild.id)
            )
            await db.commit()
        await ctx.send(f"✅ Salon de bienvenue : {channel.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT title, description, gif_url, channel_id FROM welcome WHERE guild_id = ?", (member.guild.id,))
            row = await cursor.fetchone()
        if not row or not row[3]:
            return
        title, desc, gif, channel_id = row
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        msg = await channel.send(f"```\n[CIEL OS] Nouveau citoyen : {member.name}\\nInitialisation...\n```")
        for i in range(1, 6):
            await asyncio.sleep(1)
            bars = "■" * i + "□" * (5 - i)
            await msg.edit(content=f"```\n[CIEL OS] Sauvegarde RP...\\n[{bars}] {i*20}%\\n```")
        await asyncio.sleep(1)
        await msg.delete()
        embed = discord.Embed(title=title, description=desc.format(member=member.mention), color=0x00f5d4)
        embed.set_image(url=gif)
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))