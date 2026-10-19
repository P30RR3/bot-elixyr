import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from utils.helpers import cargar_cases, guardar_cases, historial_usuario, obtener_warns, obtener_notas
from utils.ia import preguntar_ia

def dividir_texto_estetico(texto, limite=1900):
    """Divide textos largos para no sobrepasar el límite de 2000 caracteres de Discord."""
    if len(texto) <= limite: return [texto]
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte == -1: corte = limite
        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto: partes.append(texto)
    return partes

class Expedientes(commands.Cog):
    """Gestión y peritaje táctico de expedientes disciplinarios."""
    def __init__(self, bot):
        self.bot = bot

    # ─── 1. CONSULTAR CASO ESPECÍFICO ───
    @commands.hybrid_command(name="case", description="Inspecciona los detalles técnicos de un expediente por su ID")
    @app_commands.describe(case_id="Identificador numérico del caso (ej: CASE-0001)")
    @commands.has_permissions(moderate_members=True)
    async def case_cmd(self, ctx, case_id: str):
        await ctx.defer()
        cases = cargar_cases()
        
        # Formatear el ID si el usuario solo pone el número
        if case_id.isdigit():
            case_id = f"CASE-{int(case_id):04d}"
        else:
            case_id = case_id.upper()

        caso = cases.get(case_id)

        if not caso:
            return await ctx.send(f"⚠️ **[EXP-NOT-FOUND]** No existe registro del expediente `{case_id}` en la base de datos central.")

        fecha = caso.get("fecha", "Fecha no registrada")
        tipo = caso.get("tipo", "SANCIÓN").upper()
        usuario_id = caso.get("usuario_id")
        mod_id = caso.get("moderador_id")
        razon = caso.get("razon", "Sin justificación documentada")
        extra = caso.get("extra", {})

        detalles_txt = ""
        if extra:
            detalles_txt = "\n" + "\n".join([f"> • **{k.capitalize()}:** `{v}`" for k, v in extra.items()])

        panel = (
            f"### 📋 EXPEDIENTE DISCIPLINARIO `{case_id}`\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> • **Tipo de Sanción:** `{tipo}`\n"
            f"> • **Sujeto Involucrado:** <@{usuario_id}> (`{usuario_id}`)\n"
            f"> • **Oficial Asignado:** <@{mod_id}> (`{mod_id}`)\n"
            f"> • **Marca Temporal:** `{fecha}`{detalles_txt}\n\n"
            f"**Motivo Registrado:**\n"
            f"```{razon}```\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(panel)

    # ─── 2. HISTORIAL COMPLETO (DOSSIER MILITAR) ───
    @commands.hybrid_command(name="historial", aliases=["record", "cases"], description="Historial disciplinario de un miembro")
    @app_commands.describe(usuario="Miembro a investigar")
    @commands.has_permissions(moderate_members=True)
    async def historial_cmd(self, ctx, usuario: discord.Member):
        await ctx.defer()
        casos = historial_usuario(usuario.id)
        warns = obtener_warns(usuario.id)
        notas = obtener_notas(usuario.id)

        if not casos and not warns:
            return await ctx.send(f"✦ El usuario **{usuario.display_name}** (`{usuario.id}`) cuenta con un expediente totalmente limpio.")

        cabecera = (
            f"### 🗃️ DOSSIER DE ANTECEDENTES ▸ {usuario.mention}\n"
            f"> **Identificador:** `{usuario.id}` | **Casos:** `{len(casos)}` | **Warns:** `{len(warns)}` | **Notas:** `{len(notas)}`\n"
            f"✦ ────────────────────────────────────────── ✦\n"
        )

        lineas = []
        # Mostrar los últimos 8 casos para no saturar
        for c_id, c_data in list(casos.items())[-8:]:
            tipo = c_data.get("tipo", "CASO").upper()
            fecha = c_data.get("fecha", "N/A")
            razon = c_data.get("razon", "Sin razón")
            mod = f"<@{c_data.get('moderador_id')}>"
            lineas.append(f"> `{c_id}` **[{tipo}]** ({fecha}) ▸ {mod}\n> ↳ *{razon[:80]}*")

        cuerpo = "\n\n".join(lineas) if lineas else "> *No hay sanciones mayores registradas.*"
        pie = f"\n✦ ────────────────────────────────────────── ✦\n*Para obtener un dictamen psicológico con IA usa `/expediente-ia`.*"
        
        texto_completo = cabecera + cuerpo + pie
        for p in dividir_texto_estetico(texto_completo):
            await ctx.send(p)

    # ─── 3. DICTAMEN CONDUCTUAL ASISTIDO POR IA ───
    @commands.hybrid_command(name="expediente-ia", description="La IA analiza las infracciones del usuario y entrega un veredicto")
    @app_commands.describe(usuario="Miembro a auditar")
    @commands.has_permissions(moderate_members=True)
    async def expediente_ia(self, ctx, usuario: discord.Member):
        await ctx.defer()
        casos = historial_usuario(usuario.id)
        warns = obtener_warns(usuario.id)
        notas = obtener_notas(usuario.id)

        if not casos and not warns and not notas:
            return await ctx.send(f"🛡️ El usuario {usuario.mention} no registra antecedentes para perfilar.")

        resumen = [
            f"Total Sanciones: {len(casos)}",
            f"Total Advertencias: {len(warns)}",
            f"Notas del staff: {len(notas)}"
        ]
        for c_id, c_data in list(casos.items())[-5:]:
            resumen.append(f"- Sanción: {c_data.get('tipo')} por: {c_data.get('razon')}")
        for w in warns[-5:]:
            resumen.append(f"- Warn por: {w.get('razon')}")

        datos_crudos = "\n".join(resumen)
        prompt = (
            f"Eres un analista de inteligencia de seguridad conductual. Analiza el expediente disciplinario del usuario '{usuario.name}':\n"
            f"{datos_crudos}\n\n"
            f"Entrega un reporte estricto, sin saludos ni rodeos, con la siguiente estructura exacta:\n"
            f"• **PATRÓN DE CONDUCTA:** (1 frase resumiendo su comportamiento criminal o de infracciones)\n"
            f"• **NIVEL DE AMENAZA:** (Bajo / Moderado / Elevado / Crítico)\n"
            f"• **RECOMENDACIÓN TÁCTICA:** (1 recomendación estricta para el equipo de moderación)"
        )

        analisis = await preguntar_ia(prompt)
        reporte = (
            f"### 🧠 DICTAMEN CONDUCTUAL IA ▸ {usuario.mention}\n"
            f"> **Sujeto:** `{usuario.name}` | **ID:** `{usuario.id}`\n"
            f"✦ ────────────────────────────────────────── ✦\n\n"
            f"{analisis}\n\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"-# Elixyr Guard Intelligence Service"
        )
        for p in dividir_texto_estetico(reporte):
            await ctx.send(p)

    # ─── 4. ELIMINAR EXPEDIENTE ───
    @commands.hybrid_command(name="delcase", description="Elimina un caso del registro central")
    @app_commands.describe(case_id="ID del expediente a revocar (ej: 1 o CASE-0001)")
    @commands.has_permissions(administrator=True)
    async def delcase(self, ctx, case_id: str):
        await ctx.defer()
        cases = cargar_cases()
        
        if case_id.isdigit():
            case_id = f"CASE-{int(case_id):04d}"
        else:
            case_id = case_id.upper()

        if case_id not in cases:
            return await ctx.send(f"⚠️ Expediente `{case_id}` no encontrado en los archivos.")

        del cases[case_id]
        guardar_cases(cases)
        await ctx.send(f"✦ **[EXPEDIENTE PURGADO]** El registro `{case_id}` ha sido eliminado de la base de datos por {ctx.author.mention}.")

async def setup(bot):
    await bot.add_cog(Expedientes(bot))