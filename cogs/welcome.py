# cogs/welcome.py
import discord
from discord.ext import commands
import json
import os

def load_json(path, default):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/welcome.json"
        self.config = load_json(self.config_path, {})

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        if guild_id not in self.config:
            return

        cfg = self.config[guild_id]
        channel = self.bot.get_channel(int(cfg["channel"]))
        if not channel:
            return

        # Message sans majuscules
        message = f".{member.name} a rejoint seïko !"

        # Embed avec GIF animé (le texte est déjà dans l'image)
        embed = discord.Embed(
            description=message,
            color=0x000000  # Fond noir pour que le GIF ressorte bien
        )
        embed.set_image(url=cfg["gif_url"])  # ← GIF avec texte intégré
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Bienvenue sur seïko • Merci de respecter les règles")

        # Mention du rôle
        ping = ""
        if cfg.get("role"):
            role = member.guild.get_role(int(cfg["role"]))
            if role:
                ping = f"{role.mention}"

        await channel.send(content=ping, embed=embed)

    welcome = discord.SlashCommandGroup("welcome", "Configurer le message de bienvenue")

    @welcome.command(name="create", description="Configurer le message de bienvenue")
    @commands.has_permissions(administrator=True)
    async def create(self, ctx, gif_url: str, salon: discord.TextChannel):
        cfg = {
            "channel": str(salon.id),
            "role": None,
            "gif_url": gif_url
        }
        self.config[str(ctx.guild.id)] = cfg
        save_json(self.config_path, self.config)
        await ctx.respond(f"✅ Bienvenue configuré avec le GIF : {gif_url}", ephemeral=False)

    @welcome.command(name="role", description="Ajouter un rôle à donner à l’arrivée")
    @commands.has_permissions(administrator=True)
    async def role(self, ctx, rôle: discord.Role):
        gid = str(ctx.guild.id)
        if gid not in self.config:
            return await ctx.respond("❌ Configure d’abord le message avec `/welcome create`.", ephemeral=False)
        self.config[gid]["role"] = str(rôle.id)
        save_json(self.config_path, self.config)
        await ctx.respond(f"✅ Rôle {rôle.mention} ajouté à la bienvenue.", ephemeral=False)

    @welcome.command(name="test", description="Tester le message de bienvenue")
    @commands.has_permissions(administrator=True)
    async def test(self, ctx):
        gid = str(ctx.guild.id)
        if gid not in self.config:
            return await ctx.respond("❌ Bienvenue non configuré.", ephemeral=False)
        cfg = self.config[gid]
        abribus_text = f".{ctx.author.name} a rejoint seïko !"
        embed = discord.Embed(description=abribus_text, color=0x000000)
        embed.set_image(url=cfg["gif_url"])
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Test de bienvenue • seïko")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(WelcomeSystem(bot))