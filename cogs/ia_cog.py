import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
import logging
from collections import defaultdict
from utils.ia import preguntar_ia, resumir_texto

logger = logging.getLogger("ElixyrIA")

# ─────────────────────────────────────────────────────────────
#  GESTOR DE MEMORIA VIRTUAL CONVERSACIONAL
# ─────────────────────────────────────────────────────────────
MEMORIA_USUARIOS = defaultdict(dict)

MAX_HISTORIAL_TURNOS = 30   
TIEMPO_INACTIVIDAD = 7200    # 2 Horas

def _obtener_historial(user_id: int) -> list:
    ahora = time.time()
    sesion = MEMORIA_USUARIOS.get(user_id)
    if not sesion:
        return []

    if ahora - sesion.get("ultimo_acceso", 0) > TIEMPO_INACTIVIDAD:
        MEMORIA_USUARIOS[user_id] = {"ultimo_acceso": ahora, "mensajes": []}
        return []

    return list(sesion.get("mensajes", []))

def _guardar_en_memoria(user_id: int, pregunta: str, respuesta: str):
    ahora = time.time()
    mensajes = _obtener_historial(user_id)

    mensajes.append({"role": "user", "content": pregunta})
    mensajes.append({"role": "assistant", "content": respuesta})

    if len(mensajes) > MAX_HISTORIAL_TURNOS:
        mensajes = mensajes[-MAX_HISTORIAL_TURNOS:]

    MEMORIA_USUARIOS[user_id] = {
        "ultimo_acceso": ahora,
        "mensajes": mensajes
    }

def dividir_texto(texto: str, limite: int = 1900) -> list:
    if len(texto) <= limite:
        return [texto]
    fragmentos = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1: corte = texto.rfind(" ", 0, limite)
        if corte == -1: corte = limite
        fragmentos.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto: fragmentos.append(texto)
    return fragmentos

class IA(commands.Cog):
    """Módulo conversacional abierto con memoria de contexto natural."""
    def __init__(self, bot):
        self.bot = bot
        self.garbage_collector.start()

    def cog_unload(self):
        self.garbage_collector.cancel()

    # ─── RECOLECTOR DE BASURA (PREVIENE FUGAS DE RAM) ───
    @tasks.loop(minutes=30)
    async def garbage_collector(self):
        """Purga sesiones inactivas de la memoria RAM."""
        ahora = time.time()
        purgados = 0
        # Usamos list() para no modificar el dict mientras iteramos
        for uid in list(MEMORIA_USUARIOS.keys()):
            if ahora - MEMORIA_USUARIOS[uid].get("ultimo_acceso", 0) > TIEMPO_INACTIVIDAD:
                del MEMORIA_USUARIOS[uid]
                purgados += 1
        if purgados > 0:
            logger.info(f"Garbage Collector: {purgados} sesiones de IA inactivas purgadas de la RAM.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return

        es_respuesta_al_bot = False
        if message.reference and message.reference.message_id:
            try:
                ref_msg = message.reference.resolved
                if not isinstance(ref_msg, discord.Message):
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg and ref_msg.author.id == self.bot.user.id:
                    es_respuesta_al_bot = True
            except discord.NotFound:
                pass
            except Exception as e:
                logger.warning(f"Error al resolver referencia de mensaje: {e}")

        if es_respuesta_al_bot:
            async with message.channel.typing():
                historial = _obtener_historial(message.author.id)
                payload = list(historial)
                payload.append({"role": "user", "content": message.content})

                respuesta = await preguntar_ia(historial=payload)

                if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
                    logger.error(f"Fallo de inferencia IA para el usuario {message.author.id}")
                    await message.reply("Lo siento, se me fue la onda un momento con la conexión. ¿Me lo repites?", mention_author=False)
                    return

                _guardar_en_memoria(message.author.id, message.content, respuesta)

                for parte in dividir_texto(respuesta):
                    await message.reply(parte, mention_author=False)

    @commands.hybrid_command(name="ask", aliases=["ia", "chat", "pregunta"], description="Conversa libremente con la IA")
    @app_commands.describe(pregunta="¿De qué quieres hablar o qué quieres consultar?")
    async def ask(self, ctx, *, pregunta: str):
        await ctx.defer()
        historial = _obtener_historial(ctx.author.id)
        payload = list(historial)
        payload.append({"role": "user", "content": pregunta})

        respuesta = await preguntar_ia(historial=payload)

        if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
            logger.error(f"Fallo de inferencia IA en comando /ask para {ctx.author.id}")
            return await ctx.send("Disculpa, se cayó la conexión un segundo. Prueba enviando el mensaje otra vez.")

        _guardar_en_memoria(ctx.author.id, pregunta, respuesta)

        partes = dividir_texto(respuesta)
        for i, parte in enumerate(partes):
            if i == 0:
                await ctx.send(f"> 💬 *{ctx.author.display_name}:* {pregunta}\n\n{parte}")
            else:
                await ctx.send(parte)

    @commands.hybrid_command(name="olvidar", description="Inicia un chat nuevo desde cero")
    async def olvidar(self, ctx):
        if ctx.author.id in MEMORIA_USUARIOS:
            del MEMORIA_USUARIOS[ctx.author.id]
            await ctx.send("✨ **Chat reiniciado.** Olvidé lo que veníamos hablando. ¡Empezamos de cero!", ephemeral=True)
        else:
            await ctx.send("✦ Ya teníamos un chat limpio, no había nada guardado.", ephemeral=True)

    @commands.hybrid_command(name="resumir", description="Resume artículos, párrafos o textos extensos")
    async def resumir(self, ctx, *, texto: str):
        await ctx.defer()
        if len(texto) < 25:
            return await ctx.send("El texto es muy corto para resumirlo.")

        resumen = await resumir_texto(texto)
        for parte in dividir_texto(f"📋 **Aquí tienes los puntos clave:**\n\n{resumen}"):
            await ctx.send(parte)

async def setup(bot):
    await bot.add_cog(IA(bot))