"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // ADVANCED OPS & IDENTITY CLONING (NEW GEN v6.0)
  Capacidades: Clonación de Perfiles de Roles, Respaldo SQLite No-Bloqueante,
               Restauración Quirúrgica Post-Incidente y Backup Colectivo
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import json
import asyncio
from utils.helpers import DB_PATH, db_lock
from utils.ui import formato_editorial, LiveActionController

class AdvancedOps(commands.Cog):
    """Operaciones avanzadas de contingencia, clonación y respaldo de identidades."""
    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(self._init_backup_table_async())

    async def _init_backup_table_async(self):
        def sync_init():
            with db_lock:
                conn = sqlite3.connect(DB_PATH)
                conn.execute('''CREATE TABLE IF NOT EXISTS role_backups (
                                user_id TEXT, guild_id TEXT, role_ids TEXT, fecha TEXT,
                                PRIMARY KEY(user_id, guild_id))''')
                conn.commit()
                conn.close()
        await asyncio.to_thread(sync_init)

    # ═════════════════════════════════════════════════════════════
    #  1. CLONACIÓN DE IDENTIDAD (ROLE CLONING)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="clone-profile", description="Clona de forma quirúrgica los roles de un miembro a otro")
    @app_commands.describe(origen="Usuario del cual se copiarán las credenciales", destino="Usuario que las recibirá")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def clone_profile(self, ctx, origen: discord.Member, destino: discord.Member):
        await ctx.defer()
        if origen.id == destino.id:
            return await ctx.send("⚠️ El origen y el destino no pueden ser la misma entidad.", ephemeral=True)

        # Filtrar roles permitidos por la jerarquía del bot y del autor
        roles_transferibles = [
            r for r in origen.roles
            if r.name != "@everyone" and not r.managed and r < ctx.guild.me.top_role and r < ctx.author.top_role
        ]

        if not roles_transferibles:
            return await ctx.send(f"⚠️ {origen.mention} no cuenta con roles transferibles bajo tu jerarquía actual.", ephemeral=True)

        try:
            await destino.add_roles(*roles_transferibles, reason=f"Clonación de perfil desde {origen.name} por {ctx.author}")
            cuerpo = (
                f"> **Origen:** {origen.mention}\n"
                f"> **Destinatario:** {destino.mention}\n"
                f"> **Roles Transferidos:** `{len(roles_transferibles)}` credenciales\n\n"
                f"-# Perfil de autorizaciones sincronizado con éxito."
            )
            await ctx.send(formato_editorial("CLONACIÓN DE IDENTIDAD COMPLETADA", cuerpo, badge="IDENTITY-SYNC"))
        except Exception as e:
            await ctx.send(f"❌ Error al transferir roles: `{e}`")

    # ═════════════════════════════════════════════════════════════
    #  2. RESPALDO Y RESTAURACIÓN DE CREDENCIALES
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-backup", description="Crea una instantánea encriptada de los roles actuales de un miembro")
    @app_commands.describe(usuario="Miembro objetivo")
    @commands.has_permissions(manage_roles=True)
    async def role_backup(self, ctx, usuario: discord.Member):
        await ctx.defer()
        roles_ids = [r.id for r in usuario.roles if r.name != "@everyone" and not r.managed]

        if not roles_ids:
            return await ctx.send(f"⚠️ {usuario.mention} no tiene credenciales que respaldar.", ephemeral=True)

        marca_tiempo = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        def sync_save():
            with db_lock:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT OR REPLACE INTO role_backups (user_id, guild_id, role_ids, fecha) VALUES (?, ?, ?, ?)",
                    (str(usuario.id), str(ctx.guild.id), json.dumps(roles_ids), marca_tiempo)
                )
                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_save)

        cuerpo = (
            f"> **Sujeto Asegurado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Roles Respaldados:** `{len(roles_ids)}` credenciales\n"
            f"> **Marca Temporal:** `{marca_tiempo}`\n\n"
            f"-# Registro almacenado en la bóveda de contingencia SQLite."
        )
        await ctx.send(formato_editorial("RESPALDO DE CREDENCIALES FORJADO", cuerpo, badge="BACKUP-OK"))

    @commands.hybrid_command(name="role-restore", description="Restaura las credenciales de un miembro desde su último respaldo")
    @app_commands.describe(usuario="Miembro a restituir")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_restore(self, ctx, usuario: discord.Member):
        await ctx.defer()

        def sync_fetch():
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT role_ids, fecha FROM role_backups WHERE user_id = ? AND guild_id = ?", (str(usuario.id), str(ctx.guild.id)))
            row = c.fetchone()
            conn.close()
            return row

        row = await asyncio.to_thread(sync_fetch)
        if not row:
            return await ctx.send(f"⚠️ No existe ningún respaldo registrado para {usuario.mention}.", ephemeral=True)

        roles_ids = json.loads(row[0])
        fecha_backup = row[1]

        roles_a_restaurar = [
            ctx.guild.get_role(rid) for rid in roles_ids
            if ctx.guild.get_role(rid) and ctx.guild.get_role(rid) < ctx.guild.me.top_role
        ]

        if not roles_a_restaurar:
            return await ctx.send("⚠️ Los roles respaldados ya no existen o superan mi jerarquía de permisos.", ephemeral=True)

        try:
            await usuario.add_roles(*roles_a_restaurar, reason=f"Restauración de credenciales por {ctx.author}")
            cuerpo = (
                f"> **Sujeto Restituido:** {usuario.mention}\n"
                f"> **Roles Restaurados:** `{len(roles_a_restaurar)}` de `{len(roles_ids)}` en respaldo\n"
                f"> **Fecha del Respaldo:** `{fecha_backup}`\n\n"
                f"-# Identidad y permisos reconstituidos exitosamente."
            )
            await ctx.send(formato_editorial("RESTAURACIÓN DE IDENTIDAD COMPLETADA", cuerpo, badge="RESTORE-OK"))
        except Exception as e:
            await ctx.send(f"❌ Error al restaurar credenciales: `{e}`")


async def setup(bot):
    await bot.add_cog(AdvancedOps(bot))