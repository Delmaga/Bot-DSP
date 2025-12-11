import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket")
    async def ticket(self, ctx):
        """Ouvre une interface de ticket immersive."""
        async with aiosqlite.connect("data/ciel.db") as db:
            cursor = await db.execute("SELECT name, emoji, description FROM ticket_categories")
            categories = await cursor.fetchall()
        
        if not categories:
            return await ctx.send("❌ Aucune catégorie n’est configurée.", ephemeral=True)
        
        # Créer les options du menu déroulant
        options = [
            discord.SelectOption(
                label=name[:99],
                emoji=emoji or "🎫",
                description=(description or "Aucune description")[:99]
            )
            for name, emoji, description in categories
        ]

        class TicketLauncher(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)

            @discord.ui.select(placeholder="Sélectionnez une raison", options=options)
            async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
                
                selected = select.values[0]
                await interaction.response.send_message(
                    "```\n[CIEL CORE] Initialisation du protocole sécurisé...\n```",
                    ephemeral=True
                )
                
                # ÉTAPE 1 : Barre de progression 0% → 100% (5s)
                msg = await interaction.original_response()
                for i in range(1, 6):
                    bar = "█" * i + "░" * (5 - i)
                    pct = i * 20
                    await msg.edit(content=f"```\n[CIEL CORE] Ouverture du canal sécurisé...\\n[{bar}] {pct}%\\n```")
                    await asyncio.sleep(1.0)
                
                # ÉTAPE 2 : Création du salon
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Récupérer la catégorie parente liée (via /ticket cc)
                async with aiosqlite.connect("data/ciel.db") as db:
                    cur = await db.execute(
                        "SELECT target_channel_id FROM ticket_categories WHERE name = ?",
                        (selected,)
                    )
                    parent_row = await cur.fetchone()
                    parent = ctx.guild.get_channel(parent_row[0]) if parent_row and parent_row[0] else None

                channel = await ctx.guild.create_text_channel(
                    name=f"ticket-{ctx.author.name}",
                    overwrites=overwrites,
                    category=parent
                )
                
                # Enregistrer le ticket
                async with aiosqlite.connect("data/ciel.db") as db:
                    await db.execute(
                        "INSERT INTO tickets (channel_id, user_id, category) VALUES (?, ?, ?)",
                        (channel.id, ctx.author.id, selected)
                    )
                    await db.commit()
                
                # Ping du rôle (si configuré)
                ping_role_id = None
                async with aiosqlite.connect("data/ciel.db") as db:
                    cur = await db.execute("SELECT ping_role_id FROM ticket_config WHERE guild_id = ?", (ctx.guild.id,))
                    ping_row = await cur.fetchone()
                    ping_role_id = ping_row[0] if ping_row else None
                
                ping_mention = ""
                if ping_role_id:
                    role = ctx.guild.get_role(ping_role_id)
                    if role:
                        ping_mention = f"{role.mention} • "
                
                # Message final dans le ticket
                embed = discord.Embed(
                    title="`┌─┐` Système de Ticket CIEL `┌─┐`",
                    description=f"{ping_mention}Un ticket a été ouvert par {ctx.author.mention}.\n**Catégorie** : `{selected}`",
                    color=0x00f5d4
                )
                embed.set_footer(text="Cliquez sur 🔒 pour fermer ce ticket.")
                await channel.send(embed=embed, view=TicketControls())

                # Suppression auto après 24h (optionnel, mais tu l’as demandé)
                asyncio.create_task(self.auto_delete_ticket(channel, 24 * 3600))

                await msg.edit(content="✅ Votre canal sécurisé est prêt.", embed=None, view=None)

            async def auto_delete_ticket(self, channel, delay):
                await asyncio.sleep(delay)
                try:
                    embed = discord.Embed(
                        description="`[AUTO] Ce ticket a été fermé après 24h d’inactivité.`",
                        color=0xff4d4d
                    )
                    await channel.send(embed=embed)
                    await asyncio.sleep(5)
                    await channel.delete()
                except:
                    pass

        view = TicketLauncher()
        await ctx.send("Cliquez ci-dessous pour ouvrir un ticket :", view=view)

    # === COMMANDES ADMIN ===
    @commands.hybrid_group(name="ticket_categorie")
    @commands.has_permissions(administrator=True)
    async def ticket_categorie(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Utilisez `add`, `del` ou `edit`.")

    @ticket_categorie.command(name="add")
    async def add_cat(self, ctx, nom: str, emoji: str = "🎫", *, description: str = ""):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO ticket_categories (name, emoji, description) VALUES (?, ?, ?)",
                (nom, emoji, description)
            )
            await db.commit()
        await ctx.send(f"✅ Catégorie `{nom}` ajoutée.")

    @ticket_categorie.command(name="del")
    async def del_cat(self, ctx, nom: str):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("DELETE FROM ticket_categories WHERE name = ?", (nom,))
            await db.commit()
        await ctx.send(f"🗑️ Catégorie `{nom}` supprimée.")

    @ticket_categorie.command(name="edit")
    async def edit_cat(self, ctx, nom: str, nouveau_nom: str = None, nouvel_emoji: str = None, *, nouvelle_description: str = None):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT emoji, description FROM ticket_categories WHERE name = ?", (nom,))
            row = await cur.fetchone()
            if not row:
                return await ctx.send("❌ Catégorie introuvable.")
            e, d = row
            nn = nouveau_nom or nom
            ne = nouvel_emoji or e
            nd = nouvelle_description or d
            await db.execute(
                "UPDATE ticket_categories SET name = ?, emoji = ?, description = ? WHERE name = ?",
                (nn, ne, nd, nom)
            )
            await db.commit()
        await ctx.send(f"✏️ Catégorie mise à jour : `{nom}` → `{nn}`.")

    @commands.hybrid_command(name="ticket_ping")
    @commands.has_permissions(administrator=True)
    async def ticket_ping(self, ctx, role: discord.Role):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_config (
                    guild_id INTEGER PRIMARY KEY,
                    ping_role_id INTEGER
                )
            """)
            await db.execute(
                "INSERT OR REPLACE INTO ticket_config (guild_id, ping_role_id) VALUES (?, ?)",
                (ctx.guild.id, role.id)
            )
            await db.commit()
        await ctx.send(f"🔔 Rôle de notification défini : {role.mention}")

    @commands.hybrid_command(name="ticket_salon")
    @commands.has_permissions(administrator=True)
    async def ticket_salon(self, ctx, salon: discord.TextChannel):
        await ctx.send(f"📁 Les logs de ticket seront envoyés dans {salon.mention} (à implémenter).")

    @commands.hybrid_command(name="ticket_cc")
    @commands.has_permissions(administrator=True)
    async def ticket_cc(self, ctx, categorie_nom: str, parent: discord.CategoryChannel):
        async with aiosqlite.connect("data/ciel.db") as db:
            await db.execute(
                "UPDATE ticket_categories SET target_channel_id = ? WHERE name = ?",
                (parent.id, categorie_nom)
            )
            await db.commit()
        await ctx.send(f"🔀 Les tickets de la catégorie `{categorie_nom}` seront créés dans la catégorie **{parent.name}**.")

# === CONTROLES DANS LE TICKET ===
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistant

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect("data/ciel.db") as db:
            cur = await db.execute("SELECT user_id FROM tickets WHERE channel_id = ?", (interaction.channel.id,))
            row = await cur.fetchone()
        if not row:
            return await interaction.response.send_message("❌ Ce salon n’est pas un ticket.", ephemeral=True)

        owner_id = row[0]
        if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Réservé au propriétaire ou aux modérateurs.", ephemeral=True)

        await interaction.response.send_message("```\n[SYS] Fermeture du canal sécurisé...\n```")
        await asyncio.sleep(1)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(Tickets(bot))