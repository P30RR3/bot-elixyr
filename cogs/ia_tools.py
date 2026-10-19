import discord
from discord.ext import commands
from discord import app_commands
from utils.ia import preguntar_ia


def partir_mensaje(texto: str, max_chars: int = 1900):
    """Garantiza que ningún mensaje de IA exceda los 2000 caracteres de Discord."""
    if len(texto) <= max_chars:
        return [texto]
    fragmentos = []
    while len(texto) > max_chars:
        indice = texto.rfind("\n", 0, max_chars)
        if indice == -1:
            indice = texto.rfind(" ", 0, max_chars)
        if indice == -1:
            indice = max_chars
        fragmentos.append(texto[:indice].strip())
        texto = texto[indice:].strip()
    if texto:
        fragmentos.append(texto)
    return fragmentos


class IATools(commands.Cog):
    """Herramientas de inspección en tiempo real asistidas por Inteligencia Artificial."""
    def __init__(self, bot):
        self.bot = bot

    # 1. ANÁLISIS DE CLIMA DEL CHAT
    @commands.hybrid_command(name="ia-analyze-chat", description="La IA evalúa los últimos 30 mensajes para medir la tensión del canal")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, view_channel=True)
    async def ia_analyze_chat(self, ctx):
        await ctx.defer()
        
        mensajes = []
        try:
            async for m in ctx.channel.history(limit=30):
                if not m.author.bot and m.content:
                    mensajes.append(f"{m.author.name}: {m.content}")
        except discord.Forbidden:
            return await ctx.send("⛔ **Acceso denegado:** No tengo el permiso `Leer el historial de mensajes` en este canal.")

        if len(mensajes) < 4:
            return await ctx.send("⚠️ No hay suficiente actividad reciente en este canal para generar telemetría.")

        muestra = "\n".join(reversed(mensajes))
        prompt = (
            f"Actúa como un psicólogo y analista de seguridad de comunidades. Analiza esta transcripción de Discord:\n\n"
            f"{muestra}\n\n"
            f"Entrega un diagnóstico conciso estructurado así:\n"
            f"• **Atmósfera:** (Tranquila, Tensa, Hostil, Explosiva)\n"
            f"• **Tema central:** (De qué debaten brevemente)\n"
            f"• **Focos de conflicto:** (Menciona quiénes causan fricción o si todo fluye)\n"
            f"• **Protocolo sugerido:** (Acción para el staff)"
        )
        reporte = await preguntar_ia(prompt)
        
        encabezado = (
            f"# 📡 DIAGNÓSTICO DE AMBIENTE // #{ctx.channel.name}\n"
            f"> Mensajes analizados: `{len(mensajes)}` | Canal: {ctx.channel.mention}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        texto_completo = encabezado + reporte
        
        for parte in partir_mensaje(texto_completo):
            await ctx.send(parte)

    # 2. SENTIMIENTO DE USUARIO
    @commands.hybrid_command(name="ia-sentiment", description="Analiza el comportamiento reciente de un usuario en el chat")
    @app_commands.describe(usuario="Miembro a investigar")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, view_channel=True)
    async def ia_sentiment(self, ctx, usuario: discord.Member):
        await ctx.defer()
        
        mensajes_usuario = []
        try:
            async for m in ctx.channel.history(limit=100):
                if m.author.id == usuario.id and m.content:
                    mensajes_usuario.append(m.content)
                if len(mensajes_usuario) >= 15:
                    break
        except discord.Forbidden:
            return await ctx.send("⛔ **Acceso denegado:** No dispongo de permiso para leer el historial de este canal.")

        if not mensajes_usuario:
            return await ctx.send(f"⚠️ No se encontraron mensajes recientes de {usuario.mention} en este canal.")

        muestra = "\n".join(mensajes_usuario)
        prompt = (
            f"Analiza estos mensajes recientes enviados por el usuario '{usuario.name}':\n\n"
            f"{muestra}\n\n"
            f"Determina:\n"
            f"1. **Tono predominante:** (Sarcasmo, Amabilidad, Provocación, Enojo)\n"
            f"2. **Intención:** (Integrarse, trolear, llamar la atención, debatir)\n"
            f"3. **Veredicto táctico:** (Bajo riesgo, Advertir, Silenciar si reincide)"
        )
        reporte = await preguntar_ia(prompt)

        salida = (
            f"## 👤 RADIOGRAFÍA CONDUCTUAL // {usuario.name}\n"
            f"> Sujeto analizado: {usuario.mention}\n\n"
            f"{reporte}\n\n"
            f"-# Evaluación cognitiva procesada por Cerebras AI."
        )
        for p in partir_mensaje(salida):
            await ctx.send(p)

    # 3. DETECTOR DE PHISHING / ENLACES
    @commands.hybrid_command(name="ia-detect-phishing", description="Examina un enlace sospechoso en busca de estafas o robo de cuentas")
    @app_commands.describe(enlace="URL o dominio sospechoso a examinar")
    @commands.has_permissions(manage_messages=True)
    async def ia_detect_phishing(self, ctx, *, enlace: str):
        await ctx.defer()
        prompt = (
            f"Actúa como perito en ciberseguridad. Analiza este link sospechoso recibido en Discord: '{enlace}'.\n"
            f"¿Es un intento de phishing de Discord Nitro, Steam, token-stealer, scam cripto o sitio legítimo?\n"
            f"Responde: 1. Nivel de Amenaza (Baja, Media, Crítica), 2. Explicación del truco o vector de ataque, 3. Medida recomendada."
        )
        reporte = await preguntar_ia(prompt)

        salida = (
            f"# 🛡️ INSPECCIÓN FORENSE DE ENLACE\n"
            f"> **Objetivo sospechoso:** `{enlace}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{reporte}\n\n"
            f"-# ⚠️ No ingrese a enlaces no verificados."
        )
        await ctx.send(salida)

    # 4. EVALUADOR DE REGLAS HIPOTÉTICAS
    @commands.hybrid_command(name="ia-rule-check", description="Pregúntale a la IA si una situación hipotética merece sanción")
    @app_commands.describe(caso="Describe el altercado o conducta a evaluar")
    @commands.has_permissions(manage_messages=True)
    async def ia_rule_check(self, ctx, *, caso: str):
        await ctx.defer()
        prompt = (
            f"Eres el tribunal de arbitraje de un servidor. Evalúa este caso ocurrido:\n"
            f"\"{caso}\"\n\n"
            f"Dictamina: Nivel de gravedad (Leve, Moderado, Grave), falta a la convivencia cometida y castigo recomendado exacto (Warn, Mute X min, Ban)."
        )
        reporte = await preguntar_ia(prompt)
        salida = (
            f"## ⚖️ TRIBUNAL ARBITRAL // EVALUACIÓN DE CASO\n"
            f"> **Caso expuesto:** *\"{caso}\"*\n\n"
            f"{reporte}"
        )
        for p in partir_mensaje(salida):
            await ctx.send(p)

    # 5. SUGERENCIA PARA TICKETS
    @commands.hybrid_command(name="ia-ticket-suggest", description="La IA lee el ticket actual y sugiere una respuesta profesional al staff")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, view_channel=True)
    async def ia_ticket_suggest(self, ctx):
        await ctx.defer()
        
        mensajes = []
        try:
            async for m in ctx.channel.history(limit=15):
                if m.content:
                    mensajes.append(f"{m.author.name}: {m.content}")
        except discord.Forbidden:
            return await ctx.send("⛔ **Acceso denegado:** No tengo permisos para leer los mensajes de este ticket.")

        if not mensajes:
            return await ctx.send("⚠️ No hay mensajes en este canal para generar una sugerencia.")

        conversacion = "\n".join(reversed(mensajes))
        prompt = (
            f"Eres el asistente del equipo de soporte de un servidor. Lee la siguiente conversación de un ticket:\n\n"
            f"{conversacion}\n\n"
            f"Escribe una respuesta modelo profesional, clara y resolutiva que el moderador pueda copiar y pegar para responderle al usuario. Máximo 4 líneas."
        )
        respuesta_modelo = await preguntar_ia(prompt)
        await ctx.send(f"> 💡 **RESPUESTA SUGERIDA PARA EL STAFF (Copiar y pegar):**\n\n{respuesta_modelo}")


async def setup(bot):
    await bot.add_cog(IATools(bot))