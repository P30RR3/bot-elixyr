import discord
from discord.ext import commands
from discord import app_commands
import time
from collections import defaultdict
from utils.ia import preguntar_ia, resumir_texto

# ─────────────────────────────────────────────────────────────
#  GESTOR DE MEMORIA VIRTUAL CONVERSACIONAL (AMPLIO ALCANCE)
# ─────────────────────────────────────────────────────────────
MEMORIA_USUARIOS = defaultdict(dict)

# Capacidad masiva para que se sienta como un chat continuo y fluido
MAX_HISTORIAL_TURNOS = 30   # Retiene hasta 30 mensajes (15 turnos completos de ida y vuelta)
TIEMPO_INACTIVIDAD = 7200    # 2 Horas completas antes de reiniciar memoria por inactividad

def _obtener_historial(user_id: int) -> list:
    """Extrae el flujo de conversación activo del usuario."""
    ahora = time.time()
    sesion = MEMORIA_USUARIOS.get(user_id)
    if not sesion:
        return []

    # Solo expira si pasan 2 horas completas de silencio absoluto
    if ahora - sesion.get("ultimo_acceso", 0) > TIEMPO_INACTIVIDAD:
        MEMORIA_USUARIOS[user_id] = {"ultimo_acceso": ahora, "mensajes": []}
        return []

    return list(sesion.get("mensajes", []))

def _guardar_en_memoria(user_id: int, pregunta: str, respuesta: str):
    """Guarda los turnos de diálogo manteniendo el hilo de la charla."""
    ahora = time.time()
    mensajes = _obtener_historial(user_id)

    mensajes.append({"role": "user", "content": pregunta})
    mensajes.append({"role": "assistant", "content": respuesta})

    # Si supera el búfer masivo, va descartando los más viejos de forma transparente
    if len(mensajes) > MAX_HISTORIAL_TURNOS:
        mensajes = mensajes[-MAX_HISTORIAL_TURNOS:]

    MEMORIA_USUARIOS[user_id] = {
        "ultimo_acceso": ahora,
        "mensajes": mensajes
    }

def dividir_texto(texto: str, limite: int = 1900) -> list:
    """Divide textos extensos respetando saltos de línea y párrafos."""
    if len(texto) <= limite:
        return [texto]

    fragmentos = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = texto.rfind(" ", 0, limite)
        if corte == -1:
            corte = limite

        fragmentos.append(texto[:corte].strip())
        texto = texto[corte:].strip()

    if texto:
        fragmentos.append(texto)
    return fragmentos


class IA(commands.Cog):
    """Módulo conversacional abierto con memoria de contexto natural."""
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    #  RESPUESTAS POR MENCIÓN O RESPUESTA DIRECTA (REPLY)
    # ─────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return

        # Si el usuario responde a un mensaje previo del bot
        es_respuesta_al_bot = False
        if message.reference and message.reference.message_id:
            try:
                ref_msg = message.reference.resolved
                if not isinstance(ref_msg, discord.Message):
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg and ref_msg.author.id == self.bot.user.id:
                    es_respuesta_al_bot = True
            except Exception:
                pass

        if es_respuesta_al_bot:
            async with message.channel.typing():
                historial = _obtener_historial(message.author.id)
                payload = list(historial)
                payload.append({"role": "user", "content": message.content})

                respuesta = await preguntar_ia(historial=payload)

                if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
                    await message.reply("Lo siento, se me fue la onda un momento con la conexión. ¿Me lo repites?", mention_author=False)
                    return

                _guardar_en_memoria(message.author.id, message.content, respuesta)

                for parte in dividir_texto(respuesta):
                    await message.reply(parte, mention_author=False)

    # ─────────────────────────────────────────────────────────────
    #  COMANDO /ask (CHATEAR LIBREMENTE CON MEMORIA)
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(
        name="ask",
        aliases=["ia", "chat", "pregunta"],
        description="Conversa libremente con la IA (recuerda la charla sin límite rígido)"
    )
    @app_commands.describe(pregunta="¿De qué quieres hablar o qué quieres consultar?")
    async def ask(self, ctx, *, pregunta: str):
        await ctx.defer()

        # Recuperamos la memoria continua del usuario
        historial = _obtener_historial(ctx.author.id)
        payload = list(historial)
        payload.append({"role": "user", "content": pregunta})

        # Consulta limpia a Cerebras AI
        respuesta = await preguntar_ia(historial=payload)

        if respuesta.startswith("❌") or respuesta.startswith("⚠️"):
            await ctx.send("Disculpa, se cayó la conexión un segundo. Prueba enviando el mensaje otra vez.")
            return

        # Registramos el nuevo intercambio en la memoria
        _guardar_en_memoria(ctx.author.id, pregunta, respuesta)

        # Formato de conversación natural y limpio
        partes = dividir_texto(respuesta)
        for i, parte in enumerate(partes):
            if i == 0:
                await ctx.send(f"> 💬 *{ctx.author.display_name}:* {pregunta}\n\n{parte}")
            else:
                await ctx.send(parte)

    # ─────────────────────────────────────────────────────────────
    #  COMANDO /olvidar (RESETEO MANUAL DE CONVERSACIÓN)
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(
        name="olvidar",
        aliases=["reset-chat", "nuevo-chat"],
        description="Inicia un chat nuevo desde cero y limpia la memoria de la conversación"
    )
    async def olvidar(self, ctx):
        if ctx.author.id in MEMORIA_USUARIOS:
            del MEMORIA_USUARIOS[ctx.author.id]
            await ctx.send("✨ **Chat reiniciado.** Olvidé lo que veníamos hablando. ¡Empezamos de cero!", ephemeral=True)
        else:
            await ctx.send("✦ Ya teníamos un chat limpio, no había nada guardado.", ephemeral=True)

    # ─────────────────────────────────────────────────────────────
    #  COMANDO /resumir
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(
        name="resumir",
        aliases=["summarize"],
        description="Resume artículos, párrafos o textos extensos"
    )
    @app_commands.describe(texto="Pega el texto que quieres que sintetice")
    async def resumir(self, ctx, *, texto: str):
        await ctx.defer()
        if len(texto) < 25:
            return await ctx.send("El texto es muy corto para resumirlo, pásame algo con un poco más de contenido.")

        resumen = await resumir_texto(texto)
        partes = dividir_texto(f"📋 **Aquí tienes los puntos clave:**\n\n{resumen}")
        for parte in partes:
            await ctx.send(parte)

    # ─────────────────────────────────────────────────────────────
    #  TELEMETRÍA DE ESTADO DEL MOTOR
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="ia-status", description="Comprueba la latencia del enlace con la IA")
    @commands.has_permissions(administrator=True)
    async def ia_status(self, ctx):
        await ctx.defer()
        t0 = time.time()
        test = await preguntar_ia("Responde únicamente con la palabra: ACTIVO")
        latencia = round((time.time() - t0) * 1000)

        if "ACTIVO" in test.upper():
            await ctx.send(f"🟢 **Motor Neuronal Operativo:** Latencia de inferencia `{latencia}ms`.")
        else:
            await ctx.send(f"⚠️ **Inestabilidad detectada:** {test[:150]}")


async def setup(bot):
    await bot.add_cog(IA(bot))