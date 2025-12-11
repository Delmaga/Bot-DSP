import discord
from discord.ext import commands
import aiosqlite
import asyncio

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="welcome")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx, title: str, description: str, gif_url: str, channel: discord.TextChannel):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO welcome (guild_id, title, description, gif_url, channel_id) VALUES (?, ?, ?, ?, ?)",
                (ctx.guild.id, title, description, gif_url, channel.id)
            )
            await db.commit()
        await ctx.send("✅ Interface de bienvenue configurée !")

    @commands.hybrid_command(name="welcome_test")
    async def welcome_test(self, ctx):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT title, description, gif_url FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
            row = await cur.fetchone()
        if not row:
            return await ctx.send("❌ Aucune config.")
        title, desc, gif = row
        await self.simulate_console(ctx, ctx.author)
        embed = discord.Embed(title=title, description=desc.format(member=ctx.author.mention), color=0x00f5d4)
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="welcome_salon")
    @commands.has_permissions(administrator=True)
    async def welcome_salon(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("UPDATE welcome SET channel_id = ? WHERE guild_id = ?", (channel.id, ctx.guild.id))
            await db.commit()
        await ctx.send(f"✅ Salon défini : {channel.mention}")

    async def simulate_console(self, ctx_or_channel, member):
        channel = ctx_or_channel.channel if hasattr(ctx_or_channel, 'channel') else ctx_or_channel
        msg = await channel.send(f"```\n[CIEL OS] Authentification : {member.name}\\nScan RP en cours...\n```")
        for i in range(1, 6):
            bar = "■" * i + "□" * (5 - i)
            await msg.edit(content=f"```\n[CIEL OS] Sauvegarde des données...\\n[{bar}] {i*20}%\\n```")
            await asyncio.sleep(1)
        await msg.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT title, description, gif_url, channel_id FROM welcome WHERE guild_id = ?", (member.guild.id,))
            row = await cur.fetchone()
        if row and row[3]:
            channel = member.guild.get_channel(row[3])
            if channel:
                await self.simulate_console(channel, member)
                embed = discord.Embed(title=row[0], description=row[1].format(member=member.mention), color=0x00f5d4)
                embed.set_image(url=row[2])
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))