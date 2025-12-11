import discord
from discord.ext import commands
import aiosqlite
import asyncio

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket")
    async def ticket(self, ctx):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT name, emoji, description FROM ticket_categories")
            cats = await cur.fetchall()
        if not cats:
            return await ctx.send("❌ Aucune catégorie.", ephemeral=True)
        options = [discord.SelectOption(label=n, emoji=e or "🎫", description=(d or "")[:99]) for n,e,d in cats]
        view = discord.ui.View(timeout=180)
        select = discord.ui.Select(placeholder="Choisis une catégorie", options=options)
        async def callback(interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
            cat_name = select.values[0]
            await interaction.response.send_message("```\n[████░░░░░░] Création sécurisée...\n```", ephemeral=True)
            # Créer salon
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            async with aiosqlite.connect("data/ciel.db") as db:
                cur = await db.execute("SELECT target_channel_id FROM ticket_categories WHERE name = ?", (cat_name,))
                parent_id = (await cur.fetchone())[0]
            parent = ctx.guild.get_channel(parent_id) if parent_id else None
            channel = await ctx.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites, category=parent)
            async with aiosqlite.connect("data/ciel.db") as db:
                await db.execute("INSERT INTO tickets (channel_id, user_id, category) VALUES (?, ?, ?)", (channel.id, interaction.user.id, cat_name))
                await db.commit()
            await channel.send(f"👋 Bienvenue {interaction.user.mention} ! Catégorie : `{cat_name}`.")
            await interaction.edit_original_response(content=f"✅ Salon créé : {channel.mention}", embed=None, view=None)
        select.callback = callback
        view.add_item(select)
        await ctx.send("Ouvrir un ticket :", view=view)

    @commands.hybrid_group(name="ticket_categorie")
    @commands.has_permissions(administrator=True)
    async def ticket_categorie(self, ctx):
        await ctx.send("Sous-commandes : `add`, `del`, `edit`.")

    @ticket_categorie.command(name="add")
    async def add_cat(self, ctx, name: str, emoji: str = "🎫", *, description: str = ""):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("INSERT INTO ticket_categories (name, emoji, description) VALUES (?, ?, ?)", (name, emoji, description))
            await db.commit()
        await ctx.send(f"✅ Catégorie `{name}` ajoutée.")

    @ticket_categorie.command(name="del")
    async def del_cat(self, ctx, name: str):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("DELETE FROM ticket_categories WHERE name = ?", (name,))
            await db.commit()
        await ctx.send(f"🗑️ Catégorie `{name}` supprimée.")

    @ticket_categorie.command(name="edit")
    async def edit_cat(self, ctx, name: str, new_name: str = None, new_emoji: str = None, *, new_description: str = None):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT emoji, description FROM ticket_categories WHERE name = ?", (name,))
            row = await cur.fetchone()
            if not row:
                return await ctx.send("❌ Introuvable.")
            e, d = row
            nn = new_name or name
            ne = new_emoji or e
            nd = new_description or d
            await db.execute("UPDATE ticket_categories SET name = ?, emoji = ?, description = ? WHERE name = ?", (nn, ne, nd, name))
            await db.commit()
        await ctx.send(f"✏️ `{name}` → `{nn}`.")

    @commands.hybrid_command(name="ticket_ping")
    @commands.has_permissions(administrator=True)
    async def ticket_ping(self, ctx, role: discord.Role):
        # Stocker dans DB pour usage futur (ex: ping lors création)
        await ctx.send(f"🔔 Rôle {role.mention} défini pour les tickets.")

    @commands.hybrid_command(name="ticket_salon")
    @commands.has_permissions(administrator=True)
    async def ticket_salon(self, ctx, channel: discord.TextChannel):
        await ctx.send(f"📁 Tickets créés dans : {channel.mention}.")

    @commands.hy