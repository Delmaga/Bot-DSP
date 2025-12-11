import discord
from discord.ext import commands
import aiosqlite
import asyncio
import os
from datetime import datetime

# Créer le dossier data si absent
os.makedirs("data", exist_ok=True)
DB_PATH = "data/tickets.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_categories (
                name TEXT PRIMARY KEY,
                emoji TEXT,
                description TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_config (
                guild_id INTEGER PRIMARY KEY,
                ping_role_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                category TEXT,
                ticket_id TEXT,
                created_at TEXT
            )
        """)
        await db.commit()

class TicketControls(discord.ui.View):
    def __init__(self, ticket_id: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.green, emoji="✅")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Changer l'apparence du bouton
        button.style = discord.ButtonStyle.grey
        button.disabled = True
        button.label = "En cours"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🔧 {interaction.user.mention} prend en charge ce ticket.")

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.red, emoji="🗑️")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Vérifier si c'est le propriétaire ou un modérateur
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM tickets WHERE channel_id = ?", (interaction.channel.id,))
            row = await cursor.fetchone()
        if not row:
            return await interaction.response.send_message("❌ Ce salon n’est pas un ticket.", ephemeral=True)

        owner_id = row[0]
        if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Réservé au propriétaire ou aux modérateurs.", ephemeral=True)

        await interaction.response.send_message("🔒 Fermeture du ticket...")
        await asyncio.sleep(1.5)
        await interaction.channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(init_db())

    @commands.hybrid_command(name="ticket")
    async def ticket(self, ctx):
        """Ouvre une interface de ticket avec menu déroulant."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT name, emoji, description FROM ticket_categories")
            categories = await cursor.fetchall()
        
        if not categories:
            return await ctx.send("❌ Aucune catégorie n’est configurée. Utilisez `/ticket_categorie add`.", ephemeral=True)
        
        options = [
            discord.SelectOption(
                label=name,
                emoji=emoji or "🎫",
                description=(description or "Aucune description")[:99]
            )
            for name, emoji, description in categories
        ]

        class TicketSelectView(discord.ui.View):
            @discord.ui.select(placeholder="Choisissez une catégorie", options=options)
            async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("❌ Ce menu ne vous est pas destiné.", ephemeral=True)
                
                category = select.values[0]
                await interaction.response.send_message("```\n[████░░░░░░] Création du ticket...\n```", ephemeral=True)

                # Barre de chargement 0% → 100%
                msg = await interaction.original_response()
                for i in range(2, 6):
                    bar = "█" * i + "░" * (5 - i)
                    pct = i * 20
                    await msg.edit(content=f"```\n[███████░░░] Initialisation sécurisée...\\n[{bar}] {pct}%\\n```")
                    await asyncio.sleep(0.8)
                await msg.edit(content="✅ Ticket en cours de création...")

                # Créer le salon
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                # Générer un ID de ticket simple (timestamp ou random)
                ticket_id = str(ctx.author.id)[-4:] + str(ctx.channel.id)[-4:]
                channel_name = f"{category.lower().replace(' ', '-')}-{ticket_id}"
                channel = await ctx.guild.create_text_channel(channel_name, overwrites=overwrites)

                # Récupérer le rôle de ping
                ping_role = None
                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute("SELECT ping_role_id FROM ticket_config WHERE guild_id = ?", (ctx.guild.id,))
                    row = await cur.fetchone()
                    if row and row[0]:
                        ping_role = ctx.guild.get_role(row[0])

                ping_mention = f"{ping_role.mention} • " if ping_role else ""

                # Heure de création
                now = datetime.now().strftime("%d/%m/%Y à %H:%M")

                # Message formaté
                embed = discord.Embed(
                    description=(
                        f"{ping_mention}\n"
                        "🟦 **TICKET — Seïko**\n"
                        "───────────────────────────────────────\n\n"
                        f"📁 **Catégorie** : `{category}`\n"
                        f"👤 **Utilisateur** : {ctx.author.mention}\n"
                        f"🪪 **ID** : `{ctx.author.id}`\n"
                        f"🔢 **Ticket N°** : `{ticket_id}`\n"
                        f"🕒 **Heure** : `{now}`\n\n"
                        "───────────────────────────────────────\n"
                        "Merci de détailler votre demande.\n"
                        "Un membre du staff vous répondra sous 24-48h.\n\n"
                        "▶️ **En attente de prise en charge...**"
                    ),
                    color=0x4A90E2
                )
                await channel.send(embed=embed, view=TicketControls(ticket_id))

                # Enregistrer en DB
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "INSERT INTO tickets (channel_id, user_id, category, ticket_id, created_at) VALUES (?, ?, ?, ?, ?)",
                        (channel.id, ctx.author.id, category, ticket_id, now)
                    )
                    await db.commit()

                await msg.edit(content=f"✅ Votre ticket a été créé : {channel.mention}", embed=None, view=None)

        view = TicketSelectView(timeout=120)
        await ctx.send("Cliquez ci-dessous pour ouvrir un ticket :", view=view)

    @commands.hybrid_group(name="ticket_categorie")
    @commands.has_permissions(administrator=True)
    async def ticket_categorie(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Utilisez `add`, `del` ou `edit`.")

    @ticket_categorie.command(name="add")
    async def add_category(self, ctx, nom: str, emoji: str = "🎫", *, description: str = ""):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO ticket_categories (name, emoji, description) VALUES (?, ?, ?)",
                (nom, emoji, description)
            )
            await db.commit()
        await ctx.send(f"✅ Catégorie `{nom}` ajoutée.")

    @ticket_categorie.command(name="del")
    async def del_category(self, ctx, nom: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM ticket_categories WHERE name = ?", (nom,))
            await db.commit()
        await ctx.send(f"🗑️ Catégorie `{nom}` supprimée.")

    @commands.hybrid_command(name="ticket_ping")
    @commands.has_permissions(administrator=True)
    async def ticket_ping(self, ctx, rôle: discord.Role):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO ticket_config (guild_id, ping_role_id) VALUES (?, ?)",
                (ctx.guild.id, rôle.id)
            )
            await db.commit()
        await ctx.send(f"🔔 Rôle de notification défini : {rôle.mention}")

async def setup(bot):
    await bot.add_cog(Tickets(bot))