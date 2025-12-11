import discord
from discord.ext import commands
import aiosqlite

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *, reason: str = "Aucune raison"):
        try:
            await ctx.guild.ban(user, reason=reason)
            async with aiosqlite.connect("data/ciel.db") as db:
                await db.execute(
                    "INSERT INTO moderation_logs (action, target_id, moderator_id, reason, guild_id) VALUES (?, ?, ?, ?, ?)",
                    ("ban", user.id, ctx.author.id, reason, ctx.guild.id)
                )
                await db.commit()
            await ctx.send(f"✅ {user} a été banni pour : {reason}")
        except Exception as e:
            await ctx.send(f"❌ Erreur : {e}")

    @commands.hybrid_command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Aucune raison"):
        await member.kick(reason=reason)
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT INTO moderation_logs (action, target_id, moderator_id, reason, guild_id) VALUES (?, ?, ?, ?, ?)",
                ("kick", member.id, ctx.author.id, reason, ctx.guild.id)
            )
            await db.commit()
        await ctx.send(f"✅ {member} a été expulsé.")

    @commands.hybrid_command(name="modo")
    @commands.has_permissions(manage_messages=True)
    async def modo(self, ctx):
        view = discord.ui.View(timeout=300)
        select = discord.ui.Select(
            placeholder="Action de modération",
            options=[
                discord.SelectOption(label="Ban", emoji="🔨", value="ban"),
                discord.SelectOption(label="Kick", emoji="👢", value="kick"),
                discord.SelectOption(label="Mute", emoji="🔇", value="mute"),
            ]
        )
        async def callback(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
            await interaction.response.send_message(f"Vous avez choisi : **{select.values[0]}**. (À compléter)", ephemeral=True)
        select.callback = callback
        view.add_item(select)
        await ctx.send("🛠️ **Interface CIEL - Modération**", view=view)

async def setup(bot):
    await bot.add_cog(Moderation(bot))