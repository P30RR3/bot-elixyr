import discord
from discord.ext import commands
from utils.helpers import actualizar_guild_config
from utils.ui import embed_exito
import logging

logger = logging.getLogger("ElixyrCore")

class SystemCore(commands.Cog):
    """Núcleo del sistema: Inicialización autónoma y Secure by Default."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Se dispara en el milisegundo en que el bot entra a un servidor nuevo."""
        logger.info(f"Infiltración exitosa en nueva red: {guild.name} ({guild.id})")
        
        try:
            # 1. Crear la Bóveda SOC (Categoría y Canal Privado)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
            }
            
            categoria = await guild.create_category("🛡️ ELIXYR SOC", overwrites=overwrites, reason="Auto-Setup: Bóveda de Seguridad")
            canal_logs = await guild.create_text_channel("telemetria-soc", category=categoria, reason="Auto-Setup: Canal de Logs")

            # 2. Escribir en la Base de Datos (SQLite)
            actualizar_guild_config(guild.id, "audit_channel", canal_logs.id)
            actualizar_guild_config(guild.id, "log_channel", canal_logs.id)
            actualizar_guild_config(guild.id, "automod_enabled", True)
            actualizar_guild_config(guild.id, "antiraid_enabled", True)
            actualizar_guild_config(guild.id, "antiraid_mode", "intermedio")

            # 3. Enviar reporte al dueño del servidor
            if guild.owner:
                desc = (
                    f"He tomado el control del perímetro en **{guild.name}**.\n\n"
                    f"▸ **Bóveda SOC:** Creada en {canal_logs.mention}\n"
                    f"▸ **AutoMod IA:** `ACTIVADO`\n"
                    f"▸ **Anti-Raid:** `ACTIVADO (DEFCON 3)`\n\n"
                    f"Tu servidor está protegido desde el milisegundo cero. Usa `/terminal` en tu servidor para ajustar mis parámetros tácticos."
                )
                try:
                    await guild.owner.send(embed=embed_exito("PERÍMETRO ASEGURADO", desc))
                except discord.Forbidden:
                    pass # El dueño tiene los DMs cerrados

            # 4. Mensaje de bienvenida en el canal de logs
            await canal_logs.send(embed=embed_exito("SISTEMA EN LÍNEA", "Telemetría enrutada correctamente. Monitoreo activo."))

        except Exception as e:
            logger.error(f"Fallo crítico durante el Auto-Setup en {guild.name}: {e}")

async def setup(bot):
    await bot.add_cog(SystemCore(bot))