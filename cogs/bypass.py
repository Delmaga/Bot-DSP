import discord
from discord.ext import commands
import aiosqlite

class Bypass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group()
    @commands.has_permissions(manage_channels=True)
    async def bypass(self, ctx):
        await ctx.send("Utilisez `add`, `del`, ou `edit`.")

    @bypass.command(name="add")
    async def add_bypass(self, ctx, member: discord.Member, channel: discord.TextChannel):
        await channel.set_permissions(member, read_messages=True, send_messages=True)
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO bypass (user_id, channel_id, granted_by) VALUES (?, ?, ?)",
                (member.id, channel.id, ctx.author.id)
            )
            await db.commit()
        await ctx.send(f"✅ {member.mention} a accès à {channel.mention}.")

    @bypass.command(name="del")
    async def del_bypass(self, ctx, member: discord.Member, channel: discord.TextChannel):
        await channel.set_permissions(member, overwrite=None)
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("DELETE FROM bypass WHERE user_id = ? AND channel_id = ?", (member.id, channel.id))
            await db.commit()
        await ctx.send(f"🗑️ Accès supprimé pour {member.mention} sur {channel.mention}.")

async def setup(bot):
    await bot.add_cog(Bypass(bot))