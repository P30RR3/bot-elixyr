"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // SYSTEM CORE & AUTONOMOUS INITIALIZATION (NEW GEN v6.0)
  Capacidades: Protocolo Secure-by-Default, Despliegue de Bóveda SOC Autónoma,
               Aprovisionamiento SQLite y Enlace Directo con el Propietario
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
import logging
import asyncio
from utils.helpers import actualizar_guild_config, obtener_guild_config
from utils.ui import formato_editorial

logger = logging.getLogger("ElixyrCore")

class SystemCore(commands.Cog):
    """Núcleo del sistema: Inicialización autónoma y blindaje inmediato."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Se dispara en el milisegundo en que el bot es admitido en una nueva red."""
        logger.info(f"Despliegue perimetral iniciado en: {guild.name} ({guild.id})")

        canal_soc = None
        canal_alertas = None

        try:
            # 1. Configurar Overwrites de Seguridad Extrema para la Bóveda SOC
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    manage_channels=True,
                    read_message_history=True
                )
            }

            # 2. Despliegue de Categoría y Canales Privados del SOC
            categoria = await guild.create_category("🛡️ ELIXYR SOC BÓVEDA", overwrites=overwrites, reason="Auto-Setup: Infraestructura SOC Segura")
            canal_soc = await guild.create_text_channel("telemetria-soc", category=categoria, reason="Auto-Setup: Terminal de Logs")
            canal_alertas = await guild.create_text_channel("alertas-incidentes", category=categoria, reason="Auto-Setup: Canal de Alertas Críticas")

            # 3. Registrar Canales y Activar Postura Defensiva DEFCON 3 en Base de Datos
            actualizar_guild_config(guild.id, "audit_channel", canal_soc.id)
            actualizar_guild_config(guild.id, "log_channel", canal_soc.id)
            actualizar_guild_config(guild.id, "alert_channel", canal_alertas.id)
            actualizar_guild_config(guild.id, "automod_enabled", True)
            actualizar_guild_config(guild.id, "automod_ia", True)
            actualizar_guild_config(guild.id, "automod_mode", "intermedio")
            actualizar_guild_config(guild.id, "antiraid_enabled", True)
            actualizar_guild_config(guild.id, "antinuke_enabled", True)
            actualizar_guild_config(guild.id, "antiraid_mode", "intermedio")

            # 4. Transmisión del Memorándum de Despliegue en la Bóveda
            mensaje_bienvenida = (
                f"> **Infraestructura:** `{guild.name}` (`{guild.id}`)\n"
                f"> **Postura Inicial:** `DEFCON 3 (Intermedio)`\n"
                f"> **Firewall AutoMod IA:** `EN LÍNEA 🟢`\n"
                f"> **Escudo Anti-Raid / Anti-Nuke:** `OPERATIVO 🟢`\n\n"
                f"**Directivas de Operación:**\n"
                f"Este canal está completamente aislado de la población civil mediante permisos Zero-Trust. "
                f"Usa `/terminal` para abrir la consola de control interactivo o `/server-audit` para un pentest."
            )
            await canal_soc.send(formato_editorial("BÓVEDA SOC OPERATIVA // PERÍMETRO ASEGURADO", mensaje_bienvenida, badge="DEFENSE-CORE"))

        except discord.Forbidden:
            logger.warning(f"Permisos insuficientes para crear Bóveda SOC en {guild.name}.")
        except Exception as e:
            logger.error(f"Fallo durante el auto-setup en {guild.name}: {e}")

        # 5. Despacho Informativo al Propietario de la Red
        if guild.owner:
            soc_txt = f"{canal_soc.mention}" if canal_soc else "`Permiso denegado para crear canal`"
            dossier_owner = (
                f"# 🛡️ PERÍMETRO BLINDADO // {guild.name.upper()}\n"
                f"> Elixyr Guard ha asumido la vigilancia de tu servidor de forma autónoma.\n\n"
                f"▸ **Bóveda SOC Central:** {soc_txt}\n"
                f"▸ **Modo Táctico Predeterminado:** `DEFCON 3` (Equilibrio de contención)\n"
                f"▸ **Motores Activos:** Heurística 0ms + Cerebras Cognitive Engine\n\n"
                f"Tu infraestructura se encuentra bajo protección de grado militar. "
                f"Ejecuta `/terminal` dentro de tu servidor para gestionar la postura táctica."
            )
            try:
                await guild.owner.send(dossier_owner)
            except discord.Forbidden:
                logger.info(f"DMs cerrados para el propietario de {guild.name}.")


async def setup(bot):
    await bot.add_cog(SystemCore(bot))