import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from utils.ui import ConfirmView
from utils.ia import preguntar_ia

class Purga(commands.Cog):
    """Módulo de limpieza con depuración inteligente asistida por IA."""
    def __init__(self, bot):
        self.bot = bot

    # ─── 1. PURGA INTELIGENTE POR IA (SMART PURGE) ───
    @commands.hybrid_command(
        name="purge-ia",
        description="La IA analiza los últimos mensajes y elimina solo los tóxicos o spam"
    )
    @app_commands.describe(cantidad="Cantidad de mensajes a auditar (máximo 50)")
    @commands.has_permissions(manage_messages=True)
    async def purge_ia(self, ctx, cantidad: int = 25):
        await ctx.defer(ephemeral=True)
        limite = min(max(cantidad, 5), 50)

        historial = []
        async for m in ctx.channel.history(limit=limite):
            if not m.author.bot and m.content:
                historial.append(m)

        if not historial:
            return await ctx.send("✦ No se encontraron mensajes analizables en el radar.", ephemeral=True)

        # Preparamos la muestra para la IA
        muestras = [f"ID:{m.id} | {m.author.name}: {m.content}" for m in historial]
        prompt = (
            f"Actúa como un filtro de contenido estricto de ciberseguridad. Lee estos mensajes de Discord:\n\n"
            f"{chr(10).join(muestras)}\n\n"
            f"Devuelve ÚNICAMENTE los números de ID de los mensajes que contengan: insultos, spam, provocaciones, "
            f"toxicidad, evasión de filtros o lenguaje abusivo. Sepáralos por una coma simple, ejemplo: ID1, ID2. "
            f"Si el chat está limpio y no hay ninguno, responde exactamente: NINGUNO."
        )
        
        analisis = await preguntar_ia(prompt)

        if "NINGUNO" in analisis.upper() or analisis.startswith("❌"):
            return await ctx.send("✦ **[ANÁLISIS IA]** El perímetro está limpio. No se detectaron infracciones que purgar.", ephemeral=True)

        # Extraemos solo los números de ID de la respuesta de la IA
        ids_a_borrar = [s.strip() for s in re.findall(r"\d{17,20}", analisis)]
        borrados = 0
        
        for m in historial:
            if str(m.id) in ids_a_borrar:
                try:
                    await m.delete()
                    borrados += 1
                    await asyncio.sleep(0.5) # Evitar rate-limits
                except Exception: pass

        reporte = (
            f"### 🧹 PURGA TÁCTICA IA COMPLETADA\n"
            f"> **Mensajes auditados:** `{len(historial)}`\n"
            f"> **Amenazas neutralizadas:** `{borrados}` mensajes clasificados como tóxicos/spam.\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(reporte, ephemeral=True)

    # ─── 2. PURGA GENERAL CLÁSICA ───
    @commands.hybrid_command(name="purge", aliases=["limpiar"], description="Elimina una cantidad fija de mensajes")
    @app_commands.describe(cantidad="Cantidad de mensajes a eliminar (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, cantidad: int):
        await ctx.defer(ephemeral=True)
        try:
            borrados = await ctx.channel.purge(limit=min(cantidad, 100))
            await ctx.send(f"✦ Se han purgado `{len(borrados)}` mensajes del canal exitosamente.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("⛔ **Error:** No tengo permisos para gestionar mensajes aquí.", ephemeral=True)

    # ─── 3. NUKE DE CANAL (CLONACIÓN Y DESTRUCCIÓN) ───
    @commands.hybrid_command(name="nuke-channel", description="Clona y purga el canal al 100% (Destrucción total)")
    @commands.has_permissions(administrator=True)
    async def nuke_channel(self, ctx):
        view = ConfirmView(ctx.author, timeout=30)
        aviso = (
            f"### ⚠️ PROTOCOLO DE DETONACIÓN (NUKE)\n"
            f"> Esta acción reconstruirá el canal actual y **destruirá todo el historial previo** de forma irrecuperable.\n"
            f"¿Autorizar protocolo de clonación?"
        )
        msg = await ctx.send(aviso, view=view)
        await view.wait()

        if not view.valor:
            return await msg.edit(content="🛑 **Operación abortada.** El canal permanece intacto.", view=None)

        canal_viejo = ctx.channel
        pos = canal_viejo.position
        cat = canal_viejo.category

        try:
            nuevo = await canal_viejo.clone(reason=f"Protocolo Nuke autorizado por {ctx.author}")
            await nuevo.edit(position=pos, category=cat)
            await canal_viejo.delete(reason=f"Nuke ejecutado por {ctx.author}")

            await nuevo.send(
                f"### ☢️ CANAL RESTABLECIDO Y PURGADO AL 100%\n"
                f"> **Oficial a cargo:** {ctx.author.mention}\n"
                f"✦ ────────────────────────────────────────── ✦",
                delete_after=15
            )
        except Exception as e:
            await ctx.send(f"⚠️ **Fallo crítico en la detonación:** `{e}`")

async def setup(bot):
    await bot.add_cog(Purga(bot))