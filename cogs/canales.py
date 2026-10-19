import discord
from discord.ext import commands
from discord import app_commands
from utils.ia import preguntar_ia
import asyncio
import json
import re

class Canales(commands.Cog):
    """Control de infraestructura, contención perimetral y despliegue asistido por IA."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. CREACIÓN QUIRÚRGICA DE CANALES CON IA
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(
        name="channel-create-ia",
        aliases=["canal-create-ia"],
        description="La IA diseña el nombre, tipo y descripción de un canal según lo que necesitas"
    )
    @app_commands.describe(
        descripcion="Explica de qué tratará el canal (ej: sala chill para escuchar música o clips de jugadas)",
        categoria="Opcional: Categoría donde deseas colocar el canal"
    )
    @commands.has_permissions(manage_channels=True)
    async def channel_create_ia(self, ctx, descripcion: str, categoria: discord.CategoryChannel = None):
        await ctx.defer()
        msg_wait = await ctx.send("🧠 *Analizando temática y optimizando configuración del canal...*")

        sys_prompt = "Eres un arquitecto de Discord. Diseñas canales óptimos. Devuelve ÚNICAMENTE un JSON válido."

        prompt = f"""Diseña un canal de Discord para este propósito:
"{descripcion}"

Devuelve SOLO este JSON:
{{
  "nombre": "nombre-kebab-case",
  "tipo": "texto" o "voz",
  "topic": "Breve descripción temática para el tema del canal (máximo 120 caracteres)",
  "slowmode": 0 a 10,
  "nsfw": false
}}"""

        respuesta = await preguntar_ia(prompt, json_mode=True, system_prompt=sys_prompt)

        try:
            match = re.search(r"\{.*\}", respuesta, re.DOTALL)
            data = json.loads(match.group(0)) if match else json.loads(respuesta)
        except Exception as e:
            return await msg_wait.edit(content=f"⚠️ **Error al procesar la respuesta de la IA:** `{e}`")

        nombre_canal = str(data.get("nombre", "canal-nuevo")).lower().replace(" ", "-")[:90]
        tipo = str(data.get("tipo", "texto")).lower()
        topic_canal = str(data.get("topic", ""))[:1024]
        slowmode = int(data.get("slowmode", 0))
        es_nsfw = bool(data.get("nsfw", False))

        try:
            if "voz" in tipo or "voice" in tipo:
                canal_nuevo = await ctx.guild.create_voice_channel(
                    name=nombre_canal,
                    category=categoria,
                    reason=f"Canal IA creado por {ctx.author}: {descripcion[:100]}"
                )
                icono = "🔊"
                extra_info = "Canal de Voz y Transmisión"
            else:
                canal_nuevo = await ctx.guild.create_text_channel(
                    name=nombre_canal,
                    category=categoria,
                    topic=topic_canal,
                    slowmode_delay=slowmode,
                    nsfw=es_nsfw,
                    reason=f"Canal IA creado por {ctx.author}: {descripcion[:100]}"
                )
                icono = "💬"
                extra_info = f"**Tema:** *{topic_canal or 'Sin descripción'}*\n> **Modo Lento:** `{slowmode}s`"

        except discord.Forbidden:
            return await msg_wait.edit(content="⛔ **Error de Permisos:** No dispongo de autorizaciones para gestionar o crear canales.")
        except Exception as err:
            return await msg_wait.edit(content=f"⚠️ **Fallo al crear el canal:** `{err}`")

        cat_txt = f"`{categoria.name}`" if categoria else "*Ninguna (Raíz)*"

        panel = (
            f"### {icono} CANAL DESPLEGADO POR IA // {canal_nuevo.mention}\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Identificador:** `{canal_nuevo.name}`\n"
            f"> **Categoría:** {cat_txt}\n"
            f"> {extra_info}\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"-# Optimizado y creado con Cerebras AI."
        )
        await msg_wait.edit(content=panel)

    # ═════════════════════════════════════════════════════════════
    #  2. CONTENCIÓN LOCAL (LOCK / UNLOCK)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="lock", description="Bloquea la escritura en el canal actual con comunicado IA")
    @app_commands.describe(motivo="Causa del cierre")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, *, motivo: str = "Reorganización operativa"):
        await ctx.defer()
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Lock por {ctx.author}: {motivo}")

        prompt = f"Actúa como un sistema de seguridad. Se bloqueó el canal #{ctx.channel.name} por '{motivo}'. Escribe un aviso formal y frío de 2 líneas pidiendo paciencia."
        aviso_ia = await preguntar_ia(prompt)

        panel = (
            f"### 🔒 CANAL ASEGURADO ▸ TRANSMISIÓN PAUSADA\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Canal:** {ctx.channel.mention}\n"
            f"> **Causa:** {motivo}\n"
            f"> **Oficial:** {ctx.author.mention}\n\n"
            f"*{aviso_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(panel)

    @commands.hybrid_command(name="unlock", description="Restaura la escritura en el canal actual")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.defer()
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlock por {ctx.author}")

        await ctx.send(
            f"### 🔓 CANAL RESTAURADO ▸ ACCESO CONCEDIDO\n"
            f"> Transmisión libre en {ctx.channel.mention} por disposición de {ctx.author.mention}.\n"
            f"✦ ────────────────────────────────────────── ✦"
        )

    # ═════════════════════════════════════════════════════════════
    #  3. CONTENCIÓN MASIVA (LOCK-ALL / UNLOCK-ALL)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="lock-all", description="Bloquea todos los canales de texto públicos simultáneamente")
    @app_commands.describe(motivo="Causa del bloqueo masivo")
    @commands.has_permissions(administrator=True)
    async def lock_all(self, ctx, *, motivo: str = "Incidente de seguridad / Ataque masivo"):
        await ctx.defer()
        bloqueados = 0

        prompt = f"Se aplicó LOCK-ALL en el servidor por '{motivo}'. Redacta un comunicado oficial de calma de 2 líneas solicitando paciencia."
        aviso_ia = await preguntar_ia(prompt)

        for ch in ctx.guild.text_channels:
            ow = ch.overwrites_for(ctx.guild.default_role)
            if ow.send_messages is not False:
                try:
                    ow.send_messages = False
                    await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Lock-All por {ctx.author}: {motivo}")
                    bloqueados += 1
                except Exception:
                    pass

        panel = (
            f"# 🚨 CONTENCIÓN MASIVA // PROTOCOLO LOCK-ALL\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Canales Bloqueados:** `{bloqueados}` áreas de texto congeladas.\n"
            f"> **Oficial a Cargo:** {ctx.author.mention}\n"
            f"> **Causa:** *{motivo}*\n\n"
            f"**📢 Comunicado Oficial (IA):**\n"
            f"> *{aviso_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(panel)

    @commands.hybrid_command(name="unlock-all", description="Desbloquea todos los canales tras un lock-all")
    @commands.has_permissions(administrator=True)
    async def unlock_all(self, ctx):
        await ctx.defer()
        restaurados = 0

        for ch in ctx.guild.text_channels:
            ow = ch.overwrites_for(ctx.guild.default_role)
            if ow.send_messages is False:
                try:
                    ow.send_messages = None
                    await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlock-All por {ctx.author}")
                    restaurados += 1
                except Exception:
                    pass

        await ctx.send(
            f"### 🔓 FIN DEL CONFINAMIENTO // UNLOCK-ALL COMPLETADO\n"
            f"> Se restauró la comunicación en `{restaurados}` canales públicos.\n"
            f"> **Oficial:** {ctx.author.mention}\n"
            f"✦ ────────────────────────────────────────── ✦"
        )

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
    @app_commands.describe(segundos="Intervalo de mensajes en segundos (0 - 21600)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, segundos: int):
        await ctx.defer()
        segundos = max(0, min(segundos, 21600))
        await ctx.channel.edit(slowmode_delay=segundos)
        msg = "✦ Modo lento desactivado." if segundos == 0 else f"✦ Modo lento establecido en `{segundos}s`."
        await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Canales(bot))