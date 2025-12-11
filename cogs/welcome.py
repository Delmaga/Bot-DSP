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

        message = f".{member.name} a rejoint seïko !"
        embed = discord.Embed(description=message, color=0x000000)
        embed.set_image(url=cfg["gif_url"])
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Bienvenue sur seïko • Merci de respecter les règles")

        ping = ""
        if cfg.get("role"):
            role = member.guild.get_role(int(cfg["role"]))
            if role:
                ping = f"{role.mention}"

        await channel.send(content=ping, embed=embed)

    # --- REMPLACEMENT DE SlashCommandGroup PAR hybrid_group ---
    @commands.hybrid_group(name="welcome", fallback="help")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Gérer le système de bienvenue."""
        await ctx.send("Utilisez les sous-commandes : `create`, `role`, `test`.", ephemeral=True)

    @welcome.command(name="create")
    async def welcome_create(self, ctx, gif_url: str, salon: discord.TextChannel):
        """Configurer le message de bienvenue."""
        cfg = {
            "channel": str(salon.id),
            "role": None,
            "gif_url": gif_url
        }
        self.config[str(ctx.guild.id)] = cfg
        save_json(self.config_path, self.config)
        await ctx.send(f"✅ Bienvenue configuré avec le GIF : {gif_url}")

    @welcome.command(name="role")
    async def welcome_role(self, ctx, rôle: discord.Role):
        """Ajouter un rôle à mentionner à l’arrivée."""
        gid = str(ctx.guild.id)
        if gid not in self.config:
            return await ctx.send("❌ Configure d’abord avec `/welcome create`.")
        self.config[gid]["role"] = str(rôle.id)
        save_json(self.config_path, self.config)
        await ctx.send(f"✅ Rôle {rôle.mention} ajouté à la bienvenue.")

    @welcome.command(name="test")
    async def welcome_test(self, ctx):
        """Tester le message de bienvenue."""
        gid = str(ctx.guild.id)
        if gid not in self.config:
            return await ctx.send("❌ Bienvenue non configuré.")
        cfg = self.config[gid]
        abribus_text = f".{ctx.author.name} a rejoint seïko !"
        embed = discord.Embed(description=abribus_text, color=0x000000)
        embed.set_image(url=cfg["gif_url"])
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Test de bienvenue • seïko")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))