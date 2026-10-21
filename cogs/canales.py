"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // PERIMETER CONTAINMENT & AI CHANNELS (NEW GEN v6.0)
  Capacidades: Creación Quirúrgica con IA (LiveAction), Lock/Unlock Táctico,
               Protocolo Masivo Lock-All/Unlock-All y Controles Perimetrales
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.ia import preguntar_ia, extraer_json
from utils.ui import formato_editorial, LiveActionController

class Canales(commands.Cog):
    """Control de infraestructura, contención perimetral y despliegue asistido por IA."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. CREACIÓN QUIRÚRGICA DE CANALES CON IA (LIVE-ACTION)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(
        name="channel-create-ia",
        description="Diseña y despliega un canal con nombre, tipo y topic optimizados por Cerebras AI"
    )
    @app_commands.describe(
        descripcion="Explica qué función cumplirá el canal",
        categoria="Categoría donde deseas emplazar el canal"
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_create_ia(self, ctx, descripcion: str, categoria: discord.CategoryChannel = None):
        await ctx.defer()

        live = LiveActionController(ctx, "Arquitectura de Canales // AI Deploy", total_pasos=3)
        await live.iniciar()

        await live.actualizar("Analizando especificaciones de tráfico y diseño del canal...", exito=True)

        prompt = f"""Diseña un canal de Discord óptimo para esta necesidad:
"{descripcion}"

Devuelve ÚNICAMENTE este formato JSON:
{{
  "nombre": "nombre-kebab-case",
  "tipo": "texto" o "voz",
  "topic": "Breve descripción formal para el encabezado (máx 100 caracteres)",
  "slowmode": 0 a 15,
  "nsfw": false
}}"""

        await live.actualizar("Consultando al motor semántico Cerebras AI...", exito=True)
        raw_ia = await preguntar_ia(prompt, json_mode=True, max_tokens=150)
        data = extraer_json(raw_ia)

        if not data:
            await live.finalizar("La IA entregó un formato de datos incomprensible.", error=True)
            return

        nombre = str(data.get("nombre", "canal-nuevo")).lower().replace(" ", "-")[:90]
        tipo = str(data.get("tipo", "texto")).lower()
        topic = str(data.get("topic", ""))[:1024]
        slowmode = int(data.get("slowmode", 0))
        nsfw = bool(data.get("nsfw", False))

        await live.actualizar(f"Forjando canal '{nombre}' en la infraestructura...", exito=True)

        try:
            if "voz" in tipo or "voice" in tipo:
                canal_nuevo = await ctx.guild.create_voice_channel(
                    name=nombre,
                    category=categoria,
                    reason=f"Canal IA por {ctx.author}: {descripcion[:60]}"
                )
                icono = "🔊"
                extra = "Sector de Transmisión de Audio y Enlace de Voz"
            else:
                canal_nuevo = await ctx.guild.create_text_channel(
                    name=nombre,
                    category=categoria,
                    topic=topic,
                    slowmode_delay=slowmode,
                    nsfw=nsfw,
                    reason=f"Canal IA por {ctx.author}: {descripcion[:60]}"
                )
                icono = "💬"
                extra = f"**Tema:** *{topic or 'Sin definir'}*\n> **Modo Lento:** `{slowmode}s` | **NSFW:** `{'Sí' if nsfw else 'No'}`"

            await live.finalizar(f"Canal {canal_nuevo.name} desplegado con éxito.", error=False)

            cat_txt = f"`{categoria.name}`" if categoria else "*Raíz del Servidor*"
            cuerpo = (
                f"> **Identificador:** {canal_nuevo.mention} (`{canal_nuevo.name}`)\n"
                f"> **Categoría Asignada:** {cat_txt}\n"
                f"> {extra}\n\n"
                f"-# Configuración calculada y forjada con Cerebras Cognitive Engine."
            )
            await ctx.channel.send(formato_editorial(f"{icono} INFRAESTRUCTURA FORJADA", cuerpo, badge="CHANNEL-BUILDER"))

        except Exception as e:
            await live.finalizar(f"Fallo durante la creación: {e}", error=True)

    # ═════════════════════════════════════════════════════════════
    #  2. CONTENCIÓN LOCAL (LOCK / UNLOCK)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="lock", description="Bloquea la escritura en el canal actual con comunicado formal IA")
    @app_commands.describe(motivo="Razón del aislamiento")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx, *, motivo: str = "Reorganización de seguridad"):
        await ctx.defer()
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = False
        ow.send_messages_in_threads = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Lock por {ctx.author}: {motivo}")

        prompt = f"Actúa como un sistema de seguridad frío y militar. Se cerró #{ctx.channel.name} por '{motivo}'. Escribe un comunicado formal de 1 línea pidiendo silencio operativo."
        aviso_ia = await preguntar_ia(prompt, max_tokens=60)
        if aviso_ia.startswith("❌") or aviso_ia.startswith("⚠️"):
            aviso_ia = "Transmisión suspendida provisionalmente por disposición del mando central."

        cuerpo = (
            f"> **Canal Asegurado:** {ctx.channel.mention}\n"
            f"> **Oficial a Cargo:** {ctx.author.mention}\n"
            f"> **Causa Informada:** *{motivo}*\n\n"
            f"**📢 Transmisión Táctica:**\n"
            f"> *{aviso_ia}*"
        )
        await ctx.send(formato_editorial("CANAL ASEGURADO // TRÁFICO SUSPENDIDO", cuerpo, badge="LOCKDOWN-LOCAL"))

    @commands.hybrid_command(name="unlock", description="Restaura la emisión libre de mensajes en el canal actual")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.defer()
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = None
        ow.send_messages_in_threads = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlock por {ctx.author}")

        cuerpo = (
            f"> Canal {ctx.channel.mention} restaurado.\n"
            f"> Frecuencia despejada por orden de {ctx.author.mention}."
        )
        await ctx.send(formato_editorial("ACCESO RESTAURADO // FRECUENCIA LIBRE", cuerpo, badge="UNLOCKED"))

    # ═════════════════════════════════════════════════════════════
    #  3. CONTENCIÓN MASIVA (LOCK-ALL / UNLOCK-ALL CON LIVE-ACTION)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="lock-all", description="Bloquea todos los canales de texto de la red simultáneamente")
    @app_commands.describe(motivo="Razón del bloqueo total de la red")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock_all(self, ctx, *, motivo: str = "Incidente de intrusión masiva"):
        await ctx.defer()

        canales = [ch for ch in ctx.guild.text_channels if ch.overwrites_for(ctx.guild.default_role).send_messages is not False]
        total = len(canales)

        live = LiveActionController(ctx, "Protocolo Lock-All Masivo", total_pasos=total if total > 0 else 1)
        await live.iniciar()

        if total == 0:
            await live.finalizar("Todos los canales de texto ya se encuentran bajo llave.", error=False)
            return

        bloqueados = 0
        for i, ch in enumerate(canales, 1):
            try:
                ow = ch.overwrites_for(ctx.guild.default_role)
                ow.send_messages = False
                ow.send_messages_in_threads = False
                await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Lock-All por {ctx.author}: {motivo}")
                bloqueados += 1
            except Exception:
                pass

            if i % 3 == 0 or i == total:
                await live.actualizar(f"Asegurando canal #{ch.name} ({i}/{total})...", exito=True)
                await asyncio.sleep(0.8)

        await live.finalizar(f"Confinamiento total completado. {bloqueados} canales congelados.", error=False)

    @commands.hybrid_command(name="unlock-all", description="Restaura la emisión en todos los canales tras un lock-all")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock_all(self, ctx):
        await ctx.defer()

        canales = [ch for ch in ctx.guild.text_channels if ch.overwrites_for(ctx.guild.default_role).send_messages is False]
        total = len(canales)

        live = LiveActionController(ctx, "Protocolo Unlock-All Masivo", total_pasos=total if total > 0 else 1)
        await live.iniciar()

        if total == 0:
            await live.finalizar("No hay canales bloqueados que restaurar.", error=False)
            return

        restaurados = 0
        for i, ch in enumerate(canales, 1):
            try:
                ow = ch.overwrites_for(ctx.guild.default_role)
                ow.send_messages = None
                ow.send_messages_in_threads = None
                await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlock-All por {ctx.author}")
                restaurados += 1
            except Exception:
                pass

            if i % 3 == 0 or i == total:
                await live.actualizar(f"Reabriendo canal #{ch.name} ({i}/{total})...", exito=True)
                await asyncio.sleep(0.8)

        await live.finalizar(f"Restauración perimetral completada. {restaurados} canales liberados.", error=False)

    # ═════════════════════════════════════════════════════════════
    #  4. VISIBILIDAD Y MODO LENTO
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="hide", description="Oculta el canal ante el rol @everyone")
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx):
        await ctx.defer(ephemeral=True)
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Hide por {ctx.author}")
        await ctx.send(f"👁️‍🗨️ Canal {ctx.channel.mention} ocultado ante `@everyone`.", ephemeral=True)

    @commands.hybrid_command(name="unhide", description="Vuelve visible el canal para @everyone")
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx):
        await ctx.defer(ephemeral=True)
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unhide por {ctx.author}")
        await ctx.send(f"👁️ Canal {ctx.channel.mention} visible nuevamente para `@everyone`.", ephemeral=True)

    @commands.hybrid_command(name="slowmode", description="Ajusta el modo lento en segundos (0 para desactivar)")
    @app_commands.describe(segundos="Segundos entre mensajes (0 a 21600)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, segundos: int):
        await ctx.defer()
        delay = max(0, min(segundos, 21600))
        await ctx.channel.edit(slowmode_delay=delay)
        txt = "Modo lento desactivado." if delay == 0 else f"Modo lento fijado en `{delay}s`."
        await ctx.send(f"⏱️ **Control de Flujo:** {txt}")


async def setup(bot):
    await bot.add_cog(Canales(bot))