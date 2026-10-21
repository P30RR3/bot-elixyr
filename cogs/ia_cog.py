"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // COGNITIVE CONVERSATIONAL CORE (NEW GEN v6.0)
  Capacidades: Memoria Virtual Acotada (Anti-Leak), Inferencia Conversacional,
               Soporte Asíncrono por Referencia y Purga de Sesiones Inactivas
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
import logging
from collections import OrderedDict
from utils.ia import preguntar_ia, resumir_texto
from utils.ui import formato_editorial

logger = logging.getLogger("ElixyrIA")

# Memoria acotada: Máximo 250 sesiones simultáneas en RAM para evitar fugas
MAX_SESIONES_ACTIVAS = 250
MAX_TURNOS_MEMORIA = 20
TIEMPO_EXPIRACION = 3600  # 1 hora

MEMORIA_LRU = OrderedDict()

def _gestionar_memoria(user_id: int) -> list:
    ahora = time.time()
    if user_id in MEMORIA_LRU:
        sesion = MEMORIA_LRU[user_id]
        if ahora - sesion.get("ultimo_acceso", 0) > TIEMPO_EXPIRACION:
            del MEMORIA_LRU[user_id]
            return []
        MEMORIA_LRU.move_to_end(user_id)
        return list(sesion.get("mensajes", []))
    return []

def _guardar_memoria(user_id: int, pregunta: str, respuesta: str):
    ahora = time.time()
    mensajes = _gestionar_memoria(user_id)
    mensajes.append({"role": "user", "content": pregunta})
    mensajes.append({"role": "assistant", "content": respuesta})

    if len(mensajes) > MAX_TURNOS_MEMORIA:
        mensajes = mensajes[-MAX_TURNOS_MEMORIA:]

    MEMORIA_LRU[user_id] = {"ultimo_acceso": ahora, "mensajes": mensajes}
    MEMORIA_LRU.move_to_end(user_id)

    # Desalojar la sesión más antigua si se excede el límite
    if len(MEMORIA_LRU) > MAX_SESIONES_ACTIVAS:
        MEMORIA_LRU.popitem(last=False)

def partir_bloques_texto(texto: str, limite: int = 1900) -> list:
    if len(texto) <= limite:
        return [texto]
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = texto.rfind(" ", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto:
        partes.append(texto)
    return partes

class IA(commands.Cog):
    """Módulo conversacional abierto con enlace neuronal persistente y memoria protegida."""
    def __init__(self, bot):
        self.bot = bot
        self.recolector_sesiones.start()

    def cog_unload(self):
        self.recolector_sesiones.cancel()

    @tasks.loop(minutes=20)
    async def recolector_sesiones(self):
        ahora = time.time()
        purgadas = 0
        for uid in list(MEMORIA_LRU.keys()):
            if ahora - MEMORIA_LRU[uid].get("ultimo_acceso", 0) > TIEMPO_EXPIRACION:
                del MEMORIA_LRU[uid]
                purgadas += 1
        if purgadas > 0:
            logger.info(f"Recolector IA: {purgadas} sesiones inactivas purgadas de la memoria RAM.")

    # ─── RESPUESTA CONVERSACIONAL POR MENCIÓN O CITA DIRECTA ───
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return

        es_mencion_directa = self.bot.user in message.mentions and not message.mention_everyone
        es_respuesta_al_bot = False

        if message.reference and message.reference.message_id:
            try:
                ref = message.reference.resolved
                if not isinstance(ref, discord.Message):
                    ref = await message.channel.fetch_message(message.reference.message_id)
                if ref and ref.author.id == self.bot.user.id:
                    es_respuesta_al_bot = True
            except Exception:
                pass

        if es_mencion_directa or es_respuesta_al_bot:
            contenido_limpio = message.clean_content.replace(f"@{self.bot.user.display_name}", "").strip()
            if not contenido_limpio:
                return

            try:
                async with message.channel.typing():
                    historial = _gestionar_memoria(message.author.id)
                    payload = list(historial)
                    payload.append({"role": "user", "content": contenido_limpio})

                    respuesta = await preguntar_ia(historial=payload, max_tokens=1000)

                    if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
                        return await message.reply("⚠️ *Micro-interrupción en el enlace neuronal con Cerebras. Reintenta tu transmisión.*", mention_author=False)

                    _guardar_memoria(message.author.id, contenido_limpio, respuesta)

                    for bloque in partir_bloques_texto(respuesta):
                        await message.reply(bloque, mention_author=False)
            except Exception as e:
                logger.error(f"Error procesando conversación interactiva: {e}")

    # ═════════════════════════════════════════════════════════════
    #  COMANDOS COGNITIVOS PRINCIPALES
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ask", aliases=["ia", "cerebras"], description="Consulta o conversa libremente con el motor cognitivo Cerebras AI")
    @app_commands.describe(pregunta="Pregunta, planteamiento o tarea para la IA")
    async def ask(self, ctx, *, pregunta: str):
        await ctx.defer()
        historial = _gestionar_memoria(ctx.author.id)
        payload = list(historial)
        payload.append({"role": "user", "content": pregunta})

        respuesta = await preguntar_ia(historial=payload, max_tokens=1200)

        if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
            return await ctx.send("⚠️ *El enlace neuronal no respondió a tiempo. Intenta formular tu consulta de nuevo.*")

        _guardar_memoria(ctx.author.id, pregunta, respuesta)

        partes = partir_bloques_texto(respuesta)
        for i, p in enumerate(partes):
            if i == 0:
                await ctx.send(f"> 💬 *{ctx.author.display_name}:* {pregunta}\n\n{p}")
            else:
                await ctx.send(p)

    @commands.hybrid_command(name="olvidar", description="Reinicia la memoria de tu conversación activa con la IA")
    async def olvidar(self, ctx):
        if ctx.author.id in MEMORIA_LRU:
            del MEMORIA_LRU[ctx.author.id]
            await ctx.send("✨ **Buffer de conversación purgado.** Empezamos desde cero.", ephemeral=True)
        else:
            await ctx.send("✦ No tenías ningún hilo de conversación activo en la memoria RAM.", ephemeral=True)

    @commands.hybrid_command(name="resumir", description="Sintetiza textos extensos o documentos en viñetas ejecutivas")
    @app_commands.describe(texto="Párrafo o documento a resumir")
    async def resumir(self, ctx, *, texto: str):
        await ctx.defer()
        if len(texto) < 30:
            return await ctx.send("⚠️ El texto proporcionado es demasiado corto para sintetizar.", ephemeral=True)

        resumen = await resumir_texto(texto)
        cuerpo = f"**Síntesis Ejecutiva:**\n\n{resumen}"
        await ctx.send(formato_editorial("RESUMEN ASISTIDO POR IA", cuerpo, badge="SYNTHESIS"))


async def setup(bot):
    await bot.add_cog(IA(bot))