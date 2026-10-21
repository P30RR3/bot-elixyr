"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // FORENSIC DOSSIER & BEHAVIORAL AI (NEW GEN v6.0)
  Capacidades: Inspección de Expedientes, Peritaje Psicométrico Asistido por IA,
               Dossier Criminal Unificado y Purgas Judiciales
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import inspect
from utils.helpers import cargar_cases, guardar_cases, historial_usuario, obtener_warns, obtener_notas, limpiar_warns
from utils.ia import preguntar_ia
from utils.ui import formato_editorial, barra_riesgo

async def _ejecutar_helper(func, *args, **kwargs):
    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return await res
    return res

def dividir_texto(texto: str, limite: int = 1900) -> list:
    if len(texto) <= limite:
        return [texto]
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto:
        partes.append(texto)
    return partes

class Expedientes(commands.Cog):
    """Gestión judicial, peritaje conductual y auditoría de antecedentes."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. CONSULTA DE EXPEDIENTE ESPECÍFICO
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="case", description="Inspecciona los pormenores técnicos de un expediente por su ID")
    @app_commands.describe(case_id="Identificador del caso (ej: CASE-00001 o 1)")
    @commands.has_permissions(moderate_members=True)
    async def case_cmd(self, ctx, case_id: str):
        await ctx.defer()
        cases = await _ejecutar_helper(cargar_cases)
        
        c_id = f"CASE-{int(case_id):05d}" if case_id.isdigit() else case_id.upper()
        caso = cases.get(c_id)

        if not caso:
            return await ctx.send(f"⚠️ **[EXPEDIENTE NO HALLADO]** El registro `{c_id}` no existe en la base de datos central.")

        tipo = caso.get("tipo", "SANCIÓN").upper()
        uid = caso.get("usuario_id")
        mid = caso.get("moderador_id")
        fecha = caso.get("fecha", "N/A")
        razon = caso.get("razon", "Sin justificación documentada")
        extra = caso.get("extra", {})

        detalles = "\n".join([f"> • **{k.capitalize()}:** `{v}`" for k, v in extra.items()]) if extra else ""

        contenido = (
            f"> • **Tipo de Medida:** `{tipo}`\n"
            f"> • **Sujeto Registrado:** <@{uid}> (`{uid}`)\n"
            f"> • **Oficial Asignado:** <@{mid}> (`{mid}`)\n"
            f"> • **Marca Temporal:** `{fecha}`\n"
            f"{detalles}\n"
            f"**Motivo Judicial:**\n"
            f"```{razon}```"
        )
        await ctx.send(formato_editorial(f"EXPEDIENTE DISCIPLINARIO // {c_id}", contenido, badge="LEGAL-SOC"))

    # ═════════════════════════════════════════════════════════════
    #  2. HISTORIAL COMPLETO (DOSSIER DE ANTECEDENTES)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="historial", aliases=["record", "dossier"], description="Dossier completo de antecedentes de un miembro")
    @app_commands.describe(usuario="Miembro a investigar")
    @commands.has_permissions(moderate_members=True)
    async def historial_cmd(self, ctx, usuario: discord.Member):
        await ctx.defer()
        casos = await _ejecutar_helper(historial_usuario, usuario.id)
        warns = await _ejecutar_helper(obtener_warns, usuario.id)
        notas = await _ejecutar_helper(obtener_notas, usuario.id)

        if not casos and not warns and not notas:
            return await ctx.send(f"✨ El expediente del sujeto **{usuario.display_name}** (`{usuario.id}`) está completamente limpio.")

        cabecera = (
            f"> **Sujeto:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Sanciones Mayores:** `{len(casos)}` | **Advertencias:** `{len(warns)}` | **Notas de Staff:** `{len(notas)}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        cuerpo_partes = []
        if casos:
            cuerpo_partes.append("### ⚖️ Sanciones Principales (Últimas 5):")
            for cid, cdata in list(casos.items())[-5:]:
                c_tipo = cdata.get("tipo", "CASO").upper()
                c_razon = cdata.get("razon", "Sin razón")[:75]
                c_mod = f"<@{cdata.get('moderador_id')}>"
                cuerpo_partes.append(f"> `{cid}` **[{c_tipo}]** ▸ {c_mod}\n> ↳ *{c_razon}*")

        if warns:
            cuerpo_partes.append("\n### ⚠️ Advertencias Disciplinarias (Últimas 5):")
            for w in warns[-5:]:
                w_razon = w.get("razon", "Sin razón")[:75]
                w_mod = f"<@{w.get('moderador_id')}>"
                cuerpo_partes.append(f"> • Advertido por {w_mod}: *{w_razon}*")

        cuerpo_completo = "\n".join(cuerpo_partes)
        texto_final = cabecera + cuerpo_completo + "\n\n-# Para obtener una perfilación psicológica usa /expediente-ia."

        for bloque in dividir_texto(formato_editorial(f"DOSSIER FORENSE // {usuario.name}", texto_final, badge="RECORDS")):
            await ctx.send(bloque)

    # ═════════════════════════════════════════════════════════════
    #  3. DICTAMEN CONDUCTUAL ASISTIDO POR IA
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="expediente-ia", description="La IA analiza la reincidencia del usuario y emite un veredicto de amenaza")
    @app_commands.describe(usuario="Miembro a perfilar")
    @commands.has_permissions(moderate_members=True)
    async def expediente_ia(self, ctx, usuario: discord.Member):
        await ctx.defer()
        casos = await _ejecutar_helper(historial_usuario, usuario.id)
        warns = await _ejecutar_helper(obtener_warns, usuario.id)
        notas = await _ejecutar_helper(obtener_notas, usuario.id)

        if not casos and not warns and not notas:
            return await ctx.send(f"🛡️ El sujeto {usuario.mention} no registra antecedentes que permitan trazar un patrón conductual.")

        resumen = [
            f"Casos formales: {len(casos)}",
            f"Advertencias acumuladas: {len(warns)}",
            f"Notas operativas: {len(notas)}"
        ]
        for cid, c in list(casos.items())[-4:]:
            resumen.append(f"- Sanción: {c.get('tipo')} por '{c.get('razon')}'")
        for w in warns[-4:]:
            resumen.append(f"- Advertencia por '{w.get('razon')}'")

        datos_crudos = "\n".join(resumen)
        prompt = (
            f"Eres un perfilador criminal y analista de comportamiento en comunidades digitales.\n"
            f"Examina los antecedentes disciplinarios del usuario '{usuario.name}':\n\n"
            f"{datos_crudos}\n\n"
            f"Emite un reporte forense estricto y sin charlas con este formato exacto:\n"
            f"• **PATRÓN DE CONDUCTA:** (1 frase directa evaluando su nivel de hostilidad y reincidencia)\n"
            f"• **NIVEL DE AMENAZA:** (Bajo / Moderado / Elevado / Crítico)\n"
            f"• **DIRECTIVA TÁCTICA:** (Recomendación estricta para el equipo de moderación)"
        )

        dictamen_ia = await preguntar_ia(prompt, max_tokens=180)
        
        # Mapeo visual de severidad
        sev = 5 if "CRÍTICO" in dictamen_ia.upper() else 4 if "ELEVADO" in dictamen_ia.upper() else 2 if "MODERADO" in dictamen_ia.upper() else 1
        
        contenido = (
            f"> **Sujeto Auditado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Índice de Amenaza Conductual:**\n{barra_riesgo(sev)}\n\n"
            f"**🧠 Evaluación Psicométrica (Cerebras AI):**\n"
            f"{dictamen_ia}"
        )

        panel = formato_editorial(f"PERFIL CONDUCTUAL // {usuario.name}", contenido, badge="BEHAVIOR-AI")
        await ctx.send(panel)

    # ═════════════════════════════════════════════════════════════
    #  4. PURGAS DISCIPLINARIAS
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="clearwarns", description="Elimina todas las advertencias acumuladas de un miembro")
    @app_commands.describe(usuario="Miembro al que se le limpiará el historial de advertencias")
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, usuario: discord.Member):
        await ctx.defer()
        borrados = await _ejecutar_helper(limpiar_warns, usuario.id)
        await ctx.send(f"✦ **Historial Saneado:** Se han eliminado `{borrados}` advertencias acumuladas de {usuario.mention}.")

    @commands.hybrid_command(name="delcase", description="Elimina un expediente de la base de datos central")
    @app_commands.describe(case_id="ID del caso a revocar (ej: 1 o CASE-00001)")
    @commands.has_permissions(administrator=True)
    async def delcase(self, ctx, case_id: str):
        await ctx.defer()
        cases = await _ejecutar_helper(cargar_cases)
        
        c_id = f"CASE-{int(case_id):05d}" if case_id.isdigit() else case_id.upper()
        if c_id not in cases:
            return await ctx.send(f"⚠️ El expediente `{c_id}` no existe en los archivos.", ephemeral=True)

        del cases[c_id]
        await _ejecutar_helper(guardar_cases, cases)
        await ctx.send(f"✦ **[EXPEDIENTE PURGADO]** El registro `{c_id}` ha sido destruido de los registros centrales.")


async def setup(bot):
    await bot.add_cog(Expedientes(bot))