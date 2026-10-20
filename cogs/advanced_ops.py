import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import json
from utils.helpers import DB_PATH, db_lock
from utils.ui import embed_exito, embed_error

class AdvancedOps(commands.Cog):
    """Operaciones Avanzadas: Clonación de perfiles y respaldos de identidad."""
    def __init__(self, bot):
        self.bot = bot
        self._init_backup_table()

    def _init_backup_table(self):
        """Crea la tabla de respaldos de roles dinámicamente si no existe."""
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''CREATE TABLE IF NOT EXISTS role_backups (
                            user_id TEXT, guild_id TEXT, role_ids TEXT, 
                            PRIMARY KEY(user_id, guild_id))''')
            conn.commit()
            conn.close()

    # ═════════════════════════════════════════════════════════════
    #  1. CLONACIÓN DE IDENTIDAD (ROLE CLONING)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="clone-profile", description="Clona los roles de un usuario a otro instantáneamente")
    @app_commands.describe(origen="Usuario del que se copiarán los roles", destino="Usuario que recibirá los roles")
    @commands.has_permissions(administrator=True)
    async def clone_profile(self, ctx, origen: discord.Member, destino: discord.Member):
        await ctx.defer()
        
        if origen.id == destino.id:
            return await ctx.send(embed=embed_error("Operación Inválida", "El origen y el destino no pueden ser la misma entidad."))

        # Filtrar roles: No copiar @everyone, roles de integración (bots), ni roles superiores al bot
        roles_a_copiar = [
            rol for rol in origen.roles 
            if rol.name != "@everyone" and not rol.managed and rol < ctx.guild.me.top_role and rol < ctx.author.top_role
        ]

        if not roles_a_copiar:
            return await ctx.send(embed=embed_error("Clonación Fallida", f"{origen.mention} no tiene roles transferibles por jerarquía."))

        try:
            await destino.add_roles(*roles_a_copiar, reason=f"Clonación de perfil desde {origen.name} por {ctx.author.name}")
            
            desc = (
                f"> **Origen:** {origen.mention}\n"
                f"> **Destino:** {destino.mention}\n"
                f"> **Roles Transferidos:** `{len(roles_a_copiar)}` credenciales.\n\n"
                f"**Identidad sincronizada con éxito.**"
            )
            await ctx.send(embed=embed_exito("CLONACIÓN DE IDENTIDAD COMPLETADA", desc))
        except Exception as e:
            await ctx.send(embed=embed_error("Fallo Crítico", f"Error al asignar roles: `{e}`"))

    # ═════════════════════════════════════════════════════════════
    #  2. RESPALDO DE ROLES (ROLE BACKUP)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-backup", description="Crea una copia de seguridad de los roles actuales de un usuario")
    @commands.has_permissions(manage_roles=True)
    async def role_backup(self, ctx, usuario: discord.Member):
        await ctx.defer()
        
        roles_ids = [rol.id for rol in usuario.roles if rol.name != "@everyone" and not rol.managed]
        if not roles_ids:
            return await ctx.send(embed=embed_error("Respaldo Vacío", "El usuario no tiene roles válidos para respaldar."))

        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT OR REPLACE INTO role_backups (user_id, guild_id, role_ids) VALUES (?, ?, ?)",
                         (str(usuario.id), str(ctx.guild.id), json.dumps(roles_ids)))
            conn.commit()
            conn.close()

        desc = f"> **Sujeto:** {usuario.mention}\n> **Roles Guardados:** `{len(roles_ids)}`\n\n*Los datos han sido encriptados en la bóveda del SOC.*"
        await ctx.send(embed=embed_exito("RESPALDO DE CREDENCIALES CREADO", desc))

    # ═════════════════════════════════════════════════════════════
    #  3. RESTAURACIÓN DE ROLES (ROLE RESTORE)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-restore", description="Restaura los roles de un usuario desde su última copia de seguridad")
    @commands.has_permissions(manage_roles=True)
    async def role_restore(self, ctx, usuario: discord.Member):
        await ctx.defer()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role_ids FROM role_backups WHERE user_id = ? AND guild_id = ?", (str(usuario.id), str(ctx.guild.id)))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return await ctx.send(embed=embed_error("Sin Registros", "No existe un respaldo previo para este usuario en la base de datos."))

        roles_ids = json.loads(row[0])
        roles_a_restaurar = [
            ctx.guild.get_role(rid) for rid in roles_ids 
            if ctx.guild.get_role(rid) and ctx.guild.get_role(rid) < ctx.guild.me.top_role
        ]

        if not roles_a_restaurar:
            return await ctx.send(embed=embed_error("Restauración Fallida", "Los roles respaldados ya no existen o superan mi jerarquía."))

        try:
            await usuario.add_roles(*roles_a_restaurar, reason=f"Restauración de respaldo por {ctx.author.name}")
            desc = f"> **Sujeto:** {usuario.mention}\n> **Roles Restaurados:** `{len(roles_a_restaurar)}`\n\n*Identidad recuperada exitosamente.*"
            await ctx.send(embed=embed_exito("RESTAURACIÓN DE CREDENCIALES", desc))
        except Exception as e:
            await ctx.send(embed=embed_error("Fallo Crítico", f"Error al restaurar roles: `{e}`"))

async def setup(bot):
    await bot.add_cog(AdvancedOps(bot))