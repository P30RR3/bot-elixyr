"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // AI SECURITY TOOLS & FORENSIC TELEMETRY (NEW GEN v6.0)
  Capacidades: Diagnóstico de Atmósfera del Chat (LiveAction), Radiografía
               Conductual de Usuario, Tribunal Arbitral y Copiloto de Tickets
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.ia import preguntar_ia
from utils.ui import formato_editorial, LiveActionController

def partir_mensaje(texto: str, max_chars: int = 1900) -> list:
    if len(texto) <= max_chars:
        return [texto]
    partes = []
    while len(texto) > max_chars:
        idx = texto.rfind("\n", 0, max_chars)
        if idx == -1:
            idx = max_chars
        partes.append(texto[:idx].strip())
        texto = texto[idx:].strip()
    if texto:
        partes.append(texto)
    return partes

class IATools(commands.Cog):
    """Herramientas de peritaje y análisis ambiental en tiempo real con Inteligencia Artificial."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. DIAGNÓSTICO DE ATMÓSFERA DEL CANAL (LIVE-ACTION)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ia-analyze-chat", description="Audita los últimos 30 mensajes para medir la hostilidad y tensión del chat")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True)
    async def ia_analyze_chat(self, ctx):
        await ctx.defer()

        live = LiveActionController(ctx, f"Radar de Atmósfera // #{ctx.channel.name}", total_pasos=3)
        await live.iniciar()

        await live.actualizar("Interceptando los últimos 30 paquetes de datos del canal...", exito=True)

        mensajes = []
        async for m in ctx.channel.history(limit=30):
            if not m.author.bot and m.content:
                mensajes.append(f"{m.author.name}: {m.content[:120]}")

        if len(mensajes) < 4:
            await live.finalizar("Historial insuficiente para trazar una gráfica de tensión.", error=False)
            return

        await live.actualizar(f"Inyectando {len(mensajes)} transmisiones en Cerebras Cognitive Engine...", exito=True)

        muestra = "\n".join(reversed(mensajes))
        prompt = (
            f"Actúa como un psicólogo y oficial de seguridad de comunidades digitales.\n"
            f"Analiza la siguiente transcripción reciente de Discord:\n\n"
            f"{muestra}\n\n"
            f"Entrega un diagnóstico conciso estructurado estrictamente así:\n"
            f"• **CLIMA OPERATIVO:** (Tranquilo / Tenso / Hostil / Altamente Explosivo)\n"
            f"• **TEMA CENTRAL:** (De qué debaten en 1 línea)\n"
            f"• **FOCOS DE FRICCIÓN:** (Menciona si hay usuarios generando conflicto o si la frecuencia fluye limpia)\n"
            f"• **DIRECTIVA SUGERIDA:** (Acción recomendada para el equipo de moderación)"
        )
        reporte = await preguntar_ia(prompt, max_tokens=220)
        await live.finalizar("Diagnóstico ambiental procesado con éxito.", error=False)

        cuerpo = (
            f"> **Canal Auditado:** {ctx.channel.mention}\n"
            f"> **Muestra Analizada:** `{len(mensajes)}` transmisiones captadas\n\n"
            f"**🧠 Telemetría Ambiental (Cerebras AI):**\n"
            f"{reporte}"
        )
        for bloque in partir_mensaje(formato_editorial("DIAGNÓSTICO DEL CLIMA SOCIAL", cuerpo, badge="ATMOSPHERE-SCAN")):
            await ctx.channel.send(bloque)

    # ═════════════════════════════════════════════════════════════
    #  2. RADIOGRAFÍA CONDUCTUAL DE USUARIO
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ia-sentiment", description="Analiza el comportamiento y tono reciente de un miembro en el canal")
    @app_commands.describe(usuario="Miembro a inspeccionar")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True)
    async def ia_sentiment(self, ctx, usuario: discord.Member):
        await ctx.defer()

        mensajes_usuario = []
        async for m in ctx.channel.history(limit=100):
            if m.author.id == usuario.id and m.content:
                mensajes_usuario.append(m.content[:150])
            if len(mensajes_usuario) >= 15:
                break

        if not mensajes_usuario:
            return await ctx.send(f"⚠️ No se detectó actividad reciente de {usuario.mention} en este canal.", ephemeral=True)

        prompt = (
            f"Analiza las siguientes transmisiones recientes del usuario '{usuario.name}':\n\n"
            f"{chr(10).join(mensajes_usuario)}\n\n"
            f"Determina con rigurosidad:\n"
            f"1. **Tono Predominante:** (Amigable, Provocador, Sarcástico, Agresivo, Constructivo)\n"
            f"2. **Objetivo Aparente:** (Debatir, provocar, integrarse, llamar la atención)\n"
            f"3. **Veredicto de Riesgo:** (Bajo riesgo, Monitorear de cerca, Requiere advertencia)"
        )
        reporte = await preguntar_ia(prompt, max_tokens=180)

        cuerpo = (
            f"> **Sujeto Examinado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Mensajes Muestreados:** `{len(mensajes_usuario)}` registros\n\n"
            f"**🧠 Perfil Psicométrico:**\n"
            f"{reporte}"
        )
        panel = formato_editorial(f"RADIOGRAFÍA CONDUCTUAL // {usuario.name}", cuerpo, badge="BEHAVIOR-PROFILER")
        await ctx.send(panel)

    # ═════════════════════════════════════════════════════════════
    #  3. TRIBUNAL ARBITRAL (EVALUADOR DE CASOS HIPOTÉTICOS)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ia-rule-check", description="Tribunal arbitral IA: Dictamina si un altercado o situación merece sanción")
    @app_commands.describe(caso="Explica la situación, altercado o conflicto ocurrido")
    @commands.has_permissions(moderate_members=True)
    async def ia_rule_check(self, ctx, *, caso: str):
        await ctx.defer()

        prompt = (
            f"Eres el tribunal de arbitraje y disciplina de una comunidad digital.\n"
            f"Situación expuesta:\n\"{caso}\"\n\n"
            f"Dictamina de forma severa y justa:\n"
            f"• **NIVEL DE GRAVEDAD:** (Insignificante / Leve / Grave / Crítica)\n"
            f"• **NORMATIVA VULNERADA:** (Explica la infracción ética cometida)\n"
            f"• **PENALIZACIÓN SUGERIDA:** (Ninguna / Warn / Mute X minutos / Expulsión / Ban)"
        )
        dictamen = await preguntar_ia(prompt, max_tokens=180)

        cuerpo = (
            f"> **Caso Sometido a Juicio:** *\"{caso}\"*\n"
            f"> **Oficial Consultante:** {ctx.author.mention}\n\n"
            f"**⚖️ Sentencia del Tribunal Arbitral:**\n"
            f"{dictamen}"
        )
        await ctx.send(formato_editorial("TRIBUNAL ARBITRAL // DICTAMEN LEGAL", cuerpo, badge="LEGAL-AI"))

    # ═════════════════════════════════════════════════════════════
    #  4. COPILOTO DE SOPORTE PARA TICKETS
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ia-ticket-suggest", description="La IA examina la conversación del ticket y redacta una respuesta modelo para el staff")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True)
    async def ia_ticket_suggest(self, ctx):
        await ctx.defer()

        mensajes = []
        async for m in ctx.channel.history(limit=20):
            if m.content:
                mensajes.append(f"{m.author.name}: {m.content}")

        if not mensajes:
            return await ctx.send("⚠️ No hay mensajes en este canal para analizar.", ephemeral=True)

        conversacion = "\n".join(reversed(mensajes))
        prompt = (
            f"Eres el copiloto de un equipo de soporte técnico y seguridad en Discord.\n"
            f"Conversación del caso:\n\n{conversacion[-1400:]}\n\n"
            f"Escribe una respuesta modelo profesional, concisa (máximo 3 líneas) y con resolución inmediata "
            f"para que el moderador pueda copiarla y pegarla directamente. No agregues introducciones."
        )
        sugerencia = await preguntar_ia(prompt, max_tokens=120)

        cuerpo = (
            f"> **Canal:** {ctx.channel.mention}\n\n"
            f"**💡 Respuesta Sugerida (Copiar y Pegar):**\n"
            f"```text\n{sugerencia}\n```"
        )
        await ctx.send(formato_editorial("COPILOTO DE ASISTENCIA // TICKETS", cuerpo, badge="SUPPORT-COPILOT"))


async def setup(bot):
    await bot.add_cog(IATools(bot))