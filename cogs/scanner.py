import discord
from discord.ext import commands
import re
from utils.ia import preguntar_ia, extraer_json
from utils.helpers import obtener_guild_config
from utils.ui import formato_editorial
import logging

logger = logging.getLogger("ElixyrScanner")

# Regex para detectar URLs
URL_REGEX = re.compile(r"(https?://[^\s]+)")

class MalwareScanner(commands.Cog):
    """Escáner pasivo de enlaces maliciosos asistido por IA."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot: return
        
        cfg = obtener_guild_config(message.guild.id)
        if not cfg.get("automod_enabled", True): return

        # Buscar URLs en el mensaje
        urls = URL_REGEX.findall(message.content)
        if not urls: return

        # Si hay URLs, tomamos la primera para analizarla
        url_sospechosa = urls[0]
        
        # Filtro rápido para no gastar IA en dominios obviamente seguros
        dominios_seguros = ["youtube.com", "youtu.be", "twitter.com", "x.com", "instagram.com", "tenor.com", "giphy.com", "discord.com"]
        if any(d in url_sospechosa.lower() for d in dominios_seguros):
            return

        # Análisis Forense con IA
        prompt = f"""Analiza esta URL enviada en Discord: "{url_sospechosa}"
¿Es un link de phishing (ej: discord-nitro-free), un IP logger (ej: grabify), scam de criptomonedas, o parece un link seguro?
Devuelve SOLO este JSON:
{{"malicioso": true/false, "tipo": "Phishing / IP Logger / Scam / Seguro", "riesgo": "Alto / Bajo"}}"""

        try:
            respuesta = await preguntar_ia(prompt, json_mode=True, max_tokens=80)
            data = extraer_json(respuesta)
            
            if not data: return
            
            es_malicioso = data.get("malicioso", False)
            
            if es_malicioso:
                # 1. Destruir la amenaza
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    logger.warning(f"Scanner: Sin permisos para borrar mensaje de {message.author.id}")
                    return

                # 2. Generar Reporte Forense Visual
                tipo_amenaza = data.get("tipo", "Malware Desconocido")
                riesgo = data.get("riesgo", "Alto")
                
                contenido = (
                    f"> **Sujeto Interceptado:** {message.author.mention}\n"
                    f"> **Vector de Ataque:** `{url_sospechosa}`\n"
                    f"> **Clasificación IA:** `{tipo_amenaza}`\n"
                    f"> **Nivel de Riesgo:** `{riesgo.upper()}`\n\n"
                    f"**Acción Ejecutada:** El paquete de datos ha sido destruido antes de su propagación. "
                    f"Se recomienda al personal no interactuar con enlaces no verificados."
                )
                
                reporte = formato_editorial("AMENAZA NEUTRALIZADA", contenido, badge="SANDBOX")
                await message.channel.send(reporte)
                
                # 3. Registrar en el SOC
                log_id = cfg.get("audit_channel") or cfg.get("log_channel")
                if log_id:
                    log_ch = message.guild.get_channel(int(log_id))
                    if log_ch and log_ch.id != message.channel.id:
                        await log_ch.send(reporte)

        except Exception as e:
            logger.error(f"Error en el Escáner de Malware: {e}")

async def setup(bot):
    await bot.add_cog(MalwareScanner(bot))