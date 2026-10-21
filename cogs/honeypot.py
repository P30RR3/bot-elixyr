"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // HONEYPOT DECEPTION TRAP (NEW GEN v6.0)
  Capacidades: Trampa de Contrainteligencia para Scrapers y Bots, Baneo a 0ms,
               Exención Táctica de Staff y Telemetría Forense al SOC
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ui import formato_editorial

logger = logging.getLogger("ElixyrHoneypot")

class Honeypot(commands.Cog):
    """Módulo de trampas de contrainteligencia y detección de entidades maliciosas."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="deploy-honeypot", description="Despliega un canal cebo para cazar y banear instantáneamente bots de spam")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True, ban_members=True)
    async def deploy_honeypot(self, ctx):
        await ctx.defer()
        guild = ctx.guild

        # 1. Configurar visibilidad del cebo
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        try:
            trampa = await guild.create_text_channel(
                name="gateway-auth-token",
                topic="⚠️ ADVERTENCIA: CANAL TRAMPA (HONEYPOT). SI ERES HUMANO, NO ENVÍES MENSAJES AQUÍ O SERÁS BANEADO.",
                overwrites=overwrites,
                reason="Despliegue de trampa de contrainteligencia SOC"
            )

            actualizar_guild_config(guild.id, "honeypot_channel", trampa.id)

            cebo_txt = (
                "```yaml\n"
                "[GATEWAY_AUTHENTICATION_SERVICE]\n"
                "Inserte su token de API o credencial en este canal para desbloquear permisos VIP.\n"
                "ADVERTENCIA CIVIL: Este canal está vigilado por el SOC. No transmita datos.\n"
                "```"
            )
            await trampa.send(cebo_txt)

            cuerpo = (
                f"> **Canal Trampa Desplegado:** {trampa.mention}\n"
                f"> **Vector de Contención:** Baneo Permanente a 0ms.\n\n"
                f"*Cualquier entidad que emita un mensaje en ese canal será considerada un bot hostil y erradicada.*"
            )
            await ctx.send(formato_editorial("TRAMPA HONEYPOT ACTIVA", cuerpo, badge="COUNTER-INTEL"))

        except Exception as e:
            await ctx.send(f"❌ Error al desplegar el honeypot: `{e}`")

    @commands.hybrid_command(name="remove-honeypot", description="Desmantela el canal trampa activo en el servidor")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def remove_honeypot(self, ctx):
        await ctx.defer()
        cfg = obtener_guild_config(ctx.guild.id)
        h_id = cfg.get("honeypot_channel")

        if not h_id:
            return await ctx.send("⚠️ No existe un Honeypot registrado en la base de datos.", ephemeral=True)

        canal = ctx.guild.get_channel(int(h_id))
        if canal:
            try:
                await canal.delete(reason="Desmantelamiento de Honeypot")
            except Exception:
                pass

        actualizar_guild_config(ctx.guild.id, "honeypot_channel", None)
        await ctx.send("✦ **Canal trampa desmantelado y registros purgados.**", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        cfg = obtener_guild_config(message.guild.id)
        honeypot_id = cfg.get("honeypot_channel")

        if honeypot_id and message.channel.id == int(honeypot_id):
            # Exención de seguridad: Proteger al Propietario y Administradores de auto-baneo accidental
            if message.author.id == message.guild.owner_id or message.author.guild_permissions.administrator:
                try:
                    await message.delete()
                    aviso = await message.channel.send(f"⚠️ {message.author.mention}, eres Staff. No escribas en el Honeypot.")
                    await aviso.delete(delay=5)
                except Exception:
                    pass
                return

            # NEUTRALIZACIÓN INMEDIATA (0ms)
            try:
                await message.delete()
                await message.author.ban(
                    reason="Honeypot Trigger: Activación de trampa de contrainteligencia (Posible Bot/Scraper)",
                    delete_message_seconds=86400
                )

                # Reportar alerta roja a la Bóveda SOC
                log_id = cfg.get("audit_channel") or cfg.get("log_channel")
                if log_id:
                    log_ch = message.guild.get_channel(int(log_id))
                    if log_ch:
                        alerta = (
                            f"> **Entidad Erradicada:** {message.author.mention} (`{message.author.id}`)\n"
                            f"> **Vector de Intrusión:** Transmisión de datos en canal Honeypot.\n"
                            f"> **Acción Ejecutada:** Baneo definitivo a 0ms.\n\n"
                            f"-# Contramedida de contrainteligencia ejecutada con éxito."
                        )
                        await log_ch.send(formato_editorial("INTRUSO CAZADO EN HONEYPOT", alerta, badge="TRAP-TRIGGERED"))
            except discord.Forbidden:
                logger.warning(f"Honeypot: Sin jerarquía para banear a {message.author.id}.")
            except Exception as e:
                logger.error(f"Fallo en ejecución de Honeypot: {e}")


async def setup(bot):
    await bot.add_cog(Honeypot(bot))