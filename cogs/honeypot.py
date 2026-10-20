import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ui import embed_exito, embed_error
import logging

logger = logging.getLogger("ElixyrHoneypot")

class Honeypot(commands.Cog):
    """Contrainteligencia: Despliegue de trampas para bots y raiders."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="deploy-honeypot", description="Despliega un canal trampa para cazar bots de spam y raiders")
    @commands.has_permissions(administrator=True)
    async def deploy_honeypot(self, ctx):
        await ctx.defer()
        
        # Creamos un canal que los humanos verán con una advertencia gigante, 
        # pero los bots ignorarán la advertencia y escribirán igual.
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        
        try:
            trampa = await ctx.guild.create_text_channel(
                name="gateway-auth-token", # Nombre jugoso para un bot
                topic="⚠️ CANAL TRAMPA (HONEYPOT). SI ERES HUMANO, NO ESCRIBAS AQUÍ O SERÁS BANEADO AUTOMÁTICAMENTE.",
                overwrites=overwrites,
                reason="Despliegue de Honeypot SOC"
            )
            
            # Guardamos el ID del canal trampa en la base de datos
            actualizar_guild_config(ctx.guild.id, "honeypot_channel", trampa.id)
            
            # Enviamos el cebo
            await trampa.send("```\n[SYSTEM] Ingrese su token de verificación abajo para acceder a los canales VIP.\n⚠️ ADVERTENCIA PARA HUMANOS: NO ESCRIBIR AQUÍ.\n```")
            
            await ctx.send(embed=embed_exito("HONEYPOT DESPLEGADO", f"Canal trampa creado en {trampa.mention}. Cualquier entidad que envíe un mensaje allí será erradicada al instante."))
        except Exception as e:
            await ctx.send(embed=embed_error("Fallo de Despliegue", str(e)))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot: return
        
        cfg = obtener_guild_config(message.guild.id)
        honeypot_id = cfg.get("honeypot_channel")
        
        # Si el mensaje fue enviado en el canal trampa
        if honeypot_id and message.channel.id == int(honeypot_id):
            try:
                # Borramos la evidencia y baneamos en 0ms
                await message.delete()
                await message.author.ban(reason="Auto-Ban: Activación de Honeypot (Trampa de Seguridad)")
                
                # Reportamos al SOC
                log_id = cfg.get("audit_channel") or cfg.get("log_channel")
                if log_id:
                    log_ch = message.guild.get_channel(int(log_id))
                    if log_ch:
                        alerta = (
                            f"### 🕸️ TRAMPA HONEYPOT ACTIVADA\n"
                            f"✦ ────────────────────────────────────────── ✦\n"
                            f"> **Entidad Neutralizada:** {message.author.mention} (`{message.author.id}`)\n"
                            f"> **Vector de Ataque:** Escribió en el canal trampa.\n"
                            f"> **Acción Ejecutada:** Baneo Permanente (0ms).\n"
                            f"✦ ────────────────────────────────────────── ✦"
                        )
                        await log_ch.send(alerta)
            except discord.Forbidden:
                logger.warning(f"Honeypot: Sin permisos para banear a {message.author.id} en {message.guild.name}")
            except Exception as e:
                logger.error(f"Error en ejecución de Honeypot: {e}")

async def setup(bot):
    await bot.add_cog(Honeypot(bot))