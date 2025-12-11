import discord
from discord.ext import commands
import aiosqlite
import asyncio

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(fallback="create")
    async def ticket(self, ctx):
        """Ouvre une interface de ticket"""
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT name, emoji, description FROM categories")
            categories = await cursor.fetchall()
        
        if not categories:
            return await ctx.send("❌ Aucune catégorie n'est configurée. Utilisez `/ticket categorie add`.")
        
        options = []
        for name, emoji, desc in categories:
            label = name[:100]
            desc_trim = (desc or "Aucune description")[:100]
            emoji_safe = emoji if emoji and emoji.strip() else "🎫"
            options.append(discord.SelectOption(label=label, emoji=emoji_safe, description=desc_trim))
        
        select = discord.ui.Select(
            placeholder="Choisissez une catégorie...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Ce menu ne vous est pas destiné.", ephemeral=True)
                return
            
            category_name = select.values[0]
            await interaction.response.send_message("⏳ Initialisation du canal sécurisé...", ephemeral=True)
            
            msg = await interaction.channel.send("```\n[████░░░░░░] 40% - Vérification des droits...\n```")
            await asyncio.sleep(1.2)
            await msg.edit(content="```\n[███████░░░] 70% - Attribution des permissions...\n```")
            await asyncio.sleep(1.1)
            await msg.edit(content="```\n[██████████] 100% - Canal ouvert !\n```")
            await asyncio.sleep(0.8)
            await msg.delete()
            
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            channel = await ctx.guild.create_text_channel(
                name=f"ticket-{ctx.author.name}",
                overwrites=overwrites
            )
            
            async with aiosqlite.connect("data/ciel.db") as db:
                await db.execute(
                    "INSERT INTO tickets (user_id, channel_id, category, guild_id) VALUES (?, ?, ?, ?)",
                    (ctx.author.id, channel.id, category_name, ctx.guild.id)
                )
                await db.commit()
            
            await channel.send(
                f"👋 Bienvenue {ctx.author.mention} !\n"
                f"Catégorie : **{category_name}**\n\n"
                "Un membre de l'équipe vous répondra bientôt."
            )
        
        select.callback = select_callback
        view = discord.ui.View(timeout=180)
        view.add_item(select)
        await ctx.send("Veuillez sélectionner une raison pour ouvrir un ticket :", view=view)

    @ticket.group(name="categorie", fallback="list")
    @commands.has_permissions(administrator=True)
    async def categorie(self, ctx):
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT name, emoji, description FROM categories")
            rows = await cursor.fetchall()
        if not rows:
            return await ctx.send("Aucune catégorie.")
        text = "\n".join([f"- `{name}` {emoji or ''} : {desc or ''}" for name, emoji, desc in rows])
        await ctx.send(f"Catégories :\n{text}")

    @categorie.command(name="add")
    async def add_category(self, ctx, name: str, emoji: str = "🎫", *, description: str = "Aucune description"):
        async with aiosqlite.connect("data/ciel.db") as db:
            try:
                await db.execute(
                    "INSERT INTO categories (name, emoji, description) VALUES (?, ?, ?)",
                    (name, emoji, description)
                )
                await db.commit()
                await ctx.send(f"✅ Catégorie **{name}** ajoutée !")
            except aiosqlite.IntegrityError:
                await ctx.send("❌ Cette catégorie existe déjà.")

    @categorie.command(name="del")
    async def del_category(self, ctx, name: str):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("DELETE FROM categories WHERE name = ?", (name,))
            await db.commit()
        await ctx.send(f"🗑️ Catégorie **{name}** supprimée.")

    @categorie.command(name="edit")
    async def edit_category(self, ctx, name: str, new_name: str = None, new_emoji: str = None, *, new_description: str = None):
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT emoji, description FROM categories WHERE name = ?", (name,))
            row = await cursor.fetchone()
            if not row:
                return await ctx.send("❌ Catégorie introuvable.")
            emoji, desc = row
            update_name = new_name or name
            update_emoji = new_emoji or emoji
            update_desc = new_description or desc
            await db.execute(
                "UPDATE categories SET name = ?, emoji = ?, description = ? WHERE name = ?",
                (update_name, update_emoji, update_desc, name)
            )
            await db.commit()
        await ctx.send(f"✏️ Catégorie mise à jour : **{name}** → **{update_name}**.")

async def setup(bot):
    await bot.add_cog(Tickets(bot))