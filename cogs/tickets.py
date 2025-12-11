import discord
from discord.ext import commands
import aiosqlite
import asyncio

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket")
    async def ticket(self, ctx):
        """Ouvre une interface de ticket avec menu déroulant."""
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT name, emoji, description FROM ticket_categories")
            categories = await cursor.fetchall()
        
        if not categories:
            return await ctx.send("❌ Aucune catégorie n'est configurée.", ephemeral=True)
        
        options = []
        for name, emoji, desc in categories:
            options.append(
                discord.SelectOption(
                    label=name[:99],
                    emoji=emoji or "🎫",
                    description=(desc or "Aucune description")[:99]
                )
            )
        
        class TicketView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)

            @discord.ui.select(placeholder="Sélectionnez une catégorie", options=options)
            async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("❌ Ce ticket ne vous est pas destiné.", ephemeral=True)
                    return
                
                category_name = select.values[0]
                await interaction.response.send_message("```\n[████░░░░░░] Création du canal sécurisé...\n```", ephemeral=True)
                
                # Créer le salon
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Récupérer la catégorie parente (si définie)
                async with aiosqlite.connect("data/ciel.db") as db:
                    cur = await db.execute(
                        "SELECT target_channel_id FROM ticket_categories WHERE name = ?",
                        (category_name,)
                    )
                    row = await cur.fetchone()
                    parent_id = row[0] if row and row[0] else None
                
                parent = ctx.guild.get_channel(parent_id) if parent_id else None
                
                channel = await ctx.guild.create_text_channel(
                    name=f"ticket-{ctx.author.name}",
                    overwrites=overwrites,
                    category=parent
                )
                
                # Enregistrer le ticket
                async with aiosqlite.connect("data/ciel.db") as db:
                    await db.execute(
                        "INSERT INTO tickets (channel_id, user_id, category) VALUES (?, ?, ?)",
                        (channel.id, ctx.author.id, category_name)
                    )
                    await db.commit()
                
                # Animation de chargement
                msg = await interaction.original_response()
                for i in range(2, 6):
                    bar = "■" * i + "□" * (5 - i)
                    await msg.edit(content=f"```\n[███████░░░] Attribution des droits...\\n[{bar}] {i*20}%\\n```")
                    await asyncio.sleep(0.7)
                await msg.edit(content="✅ Votre ticket a été créé !")
                await asyncio.sleep(1)
                await msg.delete()
                
                await channel.send(
                    f"👋 Bienvenue {ctx.author.mention} !\n"
                    f"**Catégorie** : `{category_name}`\n\n"
                    "Un membre de l'équipe vous répondra bientôt."
                )

        view = TicketView()
        await ctx.send("Ouvrir un ticket :", view=view)

    @commands.hybrid_group(name="ticket_categorie")
    @commands.has_permissions(administrator=True)
    async def ticket_categorie(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Utilisez `add`, `del`, ou `edit`.")

    @ticket_categorie.command(name="add")
    async def add_category(self, ctx, name: str, emoji: str = "🎫", *, description: str = ""):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO ticket_categories (name, emoji, description) VALUES (?, ?, ?)",
                (name, emoji, description)
            )
            await db.commit()
        await ctx.send(f"✅ Catégorie `{name}` ajoutée.")

    @ticket_categorie.command(name="del")
    async def del_category(self, ctx, name: str):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("DELETE FROM ticket_categories WHERE name = ?", (name,))
            await db.commit()
        await ctx.send(f"🗑️ Catégorie `{name}` supprimée.")

    @ticket_categorie.command(name="edit")
    async def edit_category(self, ctx, name: str, new_name: str = None, new_emoji: str = None, *, new_description: str = None):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT emoji, description FROM ticket_categories WHERE name = ?", (name,))
            row = await cur.fetchone()
            if not row:
                return await ctx.send("❌ Catégorie introuvable.")
            current_emoji, current_desc = row
            update_name = new_name or name
            update_emoji = new_emoji or current_emoji
            update_desc = new_description or current_desc
            await db.execute(
                "UPDATE ticket_categories SET name = ?, emoji = ?, description = ? WHERE name = ?",
                (update_name, update_emoji, update_desc, name)
            )
            await db.commit()
        await ctx.send(f"✏️ Catégorie mise à jour : `{name}` → `{update_name}`.")

    @commands.hybrid_command(name="ticket_ping")
    @commands.has_permissions(administrator=True)
    async def ticket_ping(self, ctx, role: discord.Role):
        # Optionnel : stocker dans DB pour ping auto
        await ctx.send(f"🔔 Le rôle {role.mention} sera notifié pour les tickets (à implémenter).")

    @commands.hybrid_command(name="ticket_salon")
    @commands.has_permissions(administrator=True)
    async def ticket_salon(self, ctx, channel: discord.TextChannel):
        await ctx.send(f"📁 Les tickets seront créés dans {channel.mention} (à lier à la logique).")

    @commands.hybrid_command(name="ticket_cc")
    @commands.has_permissions(administrator=True)
    async def ticket_cc(self, ctx, category_name: str, parent_channel: discord.CategoryChannel):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "UPDATE ticket_categories SET target_channel_id = ? WHERE name = ?",
                (parent_channel.id, category_name)
            )
            await db.commit()
        await ctx.send(f"🔀 Les tickets de la catégorie `{category_name}` seront créés dans la catégorie **{parent_channel.name}**.")

async def setup(bot):
    await bot.add_cog(Tickets(bot))