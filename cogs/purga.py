"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // SMART PURGE & TACTICAL DECONTAMINATION (NEW GEN v6.0)
  Capacidades: Smart Purge Asistido por IA en Ráfaga (Bulk Delete), Purga
               Paramétrica Selectiva y Protocolo Nuke Reconstructivo Total
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from datetime import datetime, timezone, timedelta
from utils.ui import ConfirmView, LiveActionController, formato_editorial
from utils.ia import preguntar_ia

class Purga(commands.Cog):
    """Módulo de limpieza, desinfección perimetral y purga táctica."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. SMART PURGE ASISTIDO POR IA (EN TIEMPO REAL)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(
        name="purge-ia",
        description="Audita con IA los últimos mensajes del canal y elimina en ráfaga solo los tóxicos/spam"
    )
    @app_commands.describe(cantidad="Cantidad de mensajes a auditar en el radar (5 a 50)")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def purge_ia(self, ctx, cantidad: int = 30):
        await ctx.defer(ephemeral=True)
        limite = min(max(cantidad, 5), 50)

        live = LiveActionController(ctx, "Smart Purge // Cerebras Engine", total_pasos=3)
        await live.iniciar()

        await live.actualizar(f"Extrayendo últimos {limite} paquetes de datos del canal...", exito=True)
        
        historial = []
        async for m in ctx.channel.history(limit=limite):
            # Solo auditar mensajes de usuarios con contenido textual
            if not m.author.bot and m.content and len(m.content.strip()) > 1:
                historial.append(m)

        if not historial:
            await live.finalizar("No se registraron mensajes analizables en el historial reciente.", error=False)
            return

        await live.actualizar(f"Inyectando {len(historial)} mensajes en el motor semántico IA...", exito=True)

        muestras = [f"ID:{m.id} | {m.author.name}: {m.content[:150]}" for m in historial]
        prompt = (
            f"Actúa como un firewall estricto de moderación en Discord. Lee estos mensajes:\n\n"
            f"{chr(10).join(muestras)}\n\n"
            f"Determina cuáles mensajes contienen: insultos graves, toxicidad, estafas, links de phishing, acoso o provocaciones evidentes.\n"
            f"Devuelve ÚNICAMENTE los números de ID separados por coma. Ejemplo: 123456789, 987654321.\n"
            f"Si todos los mensajes son limpios y seguros, responde exactamente: NINGUNO."
        )

        analisis = await preguntar_ia(prompt, max_tokens=200)

        if "NINGUNO" in analisis.upper() or analisis.startswith("❌"):
            await live.finalizar("Perímetro analizado: No se detectaron anomalías ni mensajes tóxicos.", error=False)
            return

        ids_a_borrar = set(re.findall(r"\d{17,20}", analisis))
        mensajes_para_eliminar = [m for m in historial if str(m.id) in ids_a_borrar]

        if not mensajes_para_eliminar:
            await live.finalizar("Filtro completado: Sin infracciones procesables.", error=False)
            return

        await live.actualizar(f"Neutralizando {len(mensajes_para_eliminar)} mensajes clasificados como hostiles...", exito=True)

        # ─── ELIMINACIÓN INTELIGENTE (BULK DELETE CUANDO SEA POSIBLE) ───
        ahora = datetime.now(timezone.utc)
        limite_14_dias = ahora - timedelta(days=14)
        
        recientes = [m for m in mensajes_para_eliminar if m.created_at > limite_14_dias]
        antiguos = [m for m in mensajes_para_eliminar if m.created_at <= limite_14_dias]

        borrados = 0
        if recientes:
            try:
                await ctx.channel.delete_messages(recientes)
                borrados += len(recientes)
            except Exception:
                for m in recientes:
                    try:
                        await m.delete()
                        borrados += 1
                        await asyncio.sleep(0.3)
                    except Exception:
                        pass

        for m in antiguos:
            try:
                await m.delete()
                borrados += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass

        await live.finalizar(f"Purga Quirúrgica completada. {borrados} mensajes neutralizados.", error=False)

        panel = (
            f"> **Mensajes Auditados:** `{len(historial)}`\n"
            f"> **Amenazas Eliminadas:** `{borrados}` mensajes infractores\n"
            f"> **Oficial a Cargo:** {ctx.author.mention}\n\n"
            f"-# El chat ha sido saneado mediante el motor cognitivo Cerebras."
        )
        reporte = formato_editorial("PURGA SEMÁNTICA COMPLETADA", panel, badge="PURGE-IA")
        msg_aviso = await ctx.channel.send(reporte)
        await msg_aviso.delete(delay=8)

    # ═════════════════════════════════════════════════════════════
    #  2. PURGA CLÁSICA Y PARAMÉTRICA
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="purge", aliases=["limpiar", "clear"], description="Elimina una cantidad fija de mensajes con filtros avanzados")
    @app_commands.describe(
        cantidad="Número de mensajes a eliminar (1 a 100)",
        filtro="Aplica un criterio de selección"
    )
    @app_commands.choices(filtro=[
        app_commands.Choice(name="Todos los mensajes", value="todos"),
        app_commands.Choice(name="Solo mensajes de Bots", value="bots"),
        app_commands.Choice(name="Solo mensajes con Enlaces", value="links"),
        app_commands.Choice(name="Solo Archivos / Imágenes", value="archivos"),
        app_commands.Choice(name="Solo Usuarios Humanos", value="humanos")
    ])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, cantidad: int, filtro: str = "todos"):
        await ctx.defer(ephemeral=True)
        limite = max(1, min(cantidad, 100))

        def check_filtro(m):
            if filtro == "bots":
                return m.author.bot
            if filtro == "humanos":
                return not m.author.bot
            if filtro == "links":
                return "http://" in m.content or "https://" in m.content
            if filtro == "archivos":
                return len(m.attachments) > 0
            return True

        try:
            borrados = await ctx.channel.purge(limit=limite, check=check_filtro)
            await ctx.send(f"✦ **Protocolo Purge:** Se han erradicado `{len(borrados)}` paquetes de datos del canal.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("⛔ **Error:** No dispongo de autorizaciones para borrar mensajes en este sector.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"⚠️ **Fallo al purgar mensajes:** `{e}`", ephemeral=True)

    # ═════════════════════════════════════════════════════════════
    #  3. NUKE DE CANAL RECONSTRUCTIVO
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="nuke-channel", description="Reconstruye el canal al 100% purgando todo rastro histórico")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke_channel(self, ctx):
        view = ConfirmView(ctx.author, timeout=25)
        aviso = (
            f"### ⚠️ PROTOCOLO DE RECONSTRUCCIÓN (NUKE)\n"
            f"> Esta directiva clonará la topología exacta del canal y **destruirá el canal actual con todo su historial**.\n"
            f"¿Autorizar detonación y reemplazo perimetral?"
        )
        msg = await ctx.send(aviso, view=view)
        await view.wait()

        if not view.valor:
            return await msg.edit(content="🛑 **Operación cancelada:** El canal permanece intacto.", view=None)

        canal_viejo = ctx.channel
        pos = canal_viejo.position
        cat = canal_viejo.category
        topic = canal_viejo.topic
        slow = canal_viejo.slowmode_delay
        nsfw = canal_viejo.nsfw
        overwrites = canal_viejo.overwrites

        try:
            canal_nuevo = await canal_viejo.clone(
                name=canal_viejo.name,
                reason=f"Protocolo Nuke ejecutado por {ctx.author}"
            )
            await canal_nuevo.edit(
                position=pos,
                category=cat,
                topic=topic,
                slowmode_delay=slow,
                nsfw=nsfw,
                overwrites=overwrites
            )
            await canal_viejo.delete(reason=f"Nuke ejecutado por {ctx.author}")

            panel = (
                f"# ☢️ PERÍMETRO RESTABLECIDO // PROTOCOLO NUKE\n"
                f"✦ ────────────────────────────────────────── ✦\n"
                f"> **Canal Reconstruido:** {canal_nuevo.mention}\n"
                f"> **Oficial al Mando:** {ctx.author.mention}\n"
                f"> **Estado:** Purga completa ejecutada. Red limpia.\n"
                f"✦ ────────────────────────────────────────── ✦"
            )
            await canal_nuevo.send(panel, delete_after=15)
        except Exception as e:
            await ctx.send(f"⚠️ **Fallo crítico durante el procedimiento de Nuke:** `{e}`")


async def setup(bot):
    await bot.add_cog(Purga(bot))