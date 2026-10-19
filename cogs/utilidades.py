import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timezone
from utils.helpers import cargar_config, cargar_cases
from utils.ia import preguntar_ia

CONFIG = cargar_config()
SNIPE_CACHE = {}


class PollView(discord.ui.View):
    def __init__(self, pregunta):
        super().__init__(timeout=None)
        self.pregunta = pregunta
        self.a_favor = set()
        self.en_contra = set()

    @discord.ui.button(label="A Favor (0)", style=discord.ButtonStyle.success, emoji="👍", custom_id="poll_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        self.en_contra.discard(uid)
        if uid in self.a_favor:
            self.a_favor.remove(uid)
        else:
            self.a_favor.add(uid)
        button.label = f"A Favor ({len(self.a_favor)})"
        self.children[1].label = f"En Contra ({len(self.en_contra)})"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="En Contra (0)", style=discord.ButtonStyle.danger, emoji="👎", custom_id="poll_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        self.a_favor.discard(uid)
        if uid in self.en_contra:
            self.en_contra.remove(uid)
        else:
            self.en_contra.add(uid)
        self.children[0].label = f"A Favor ({len(self.a_favor)})"
        button.label = f"En Contra ({len(self.en_contra)})"
        await interaction.response.edit_message(view=self)


class Utilidades(commands.Cog):
    """Módulo de utilidades con diseño editorial y redacción IA."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        SNIPE_CACHE[message.channel.id] = {
            "autor": message.author,
            "contenido": message.content,
            "adjunto": message.attachments[0].url if message.attachments else None,
            "hora": datetime.now(timezone.utc)
        }

    # ─────────────────────────────────────────────────────────────
    #  ANUNCIOS CON REDACCIÓN Y ESTILO ASISTIDOS POR IA
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="announce", aliases=["anuncio", "notificar"], description="La IA redacta y maqueta un anuncio profesional a partir de tu borrador")
    @app_commands.describe(
        canal="Canal donde se publicará el comunicado",
        titulo="Tema o asunto del anuncio",
        mensaje="Escribe tu borrador simple; la IA lo convertirá en un comunicado de lujo",
        estilo="Tono del comunicado",
        mencion="Mención al publicar"
    )
    @app_commands.choices(
        estilo=[
            app_commands.Choice(name="Formal y Ejecutivo", value="formal"),
            app_commands.Choice(name="Comunidad y Amistoso", value="amigable"),
            app_commands.Choice(name="Urgente / Alerta Crítica", value="alerta"),
            app_commands.Choice(name="Cyberpunk / Táctico", value="tactico"),
        ],
        mencion=[
            app_commands.Choice(name="Sin mención", value="none"),
            app_commands.Choice(name="@everyone", value="everyone"),
            app_commands.Choice(name="@here", value="here"),
        ]
    )
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx, canal: discord.TextChannel, titulo: str, *, mensaje: str, estilo: str = "formal", mencion: str = "none"):
        await ctx.defer(ephemeral=True)

        # Prompt para convertir un borrador simple en diseño editorial con Markdown de Discord
        prompt = (
            f"Eres un experto en diseño gráfico editorial y redactor oficial de servidores de Discord de lujo.\n"
            f"Transforma el siguiente borrador simple en un comunicado visualmente hermoso, limpio y estructurado.\n\n"
            f"Asunto: '{titulo}'\n"
            f"Tono seleccionado: {estilo}\n"
            f"Borrador original: \"{mensaje}\"\n\n"
            f"Directrices de formato OBLIGATORIAS:\n"
            f"1. Usa encabezados (# para título principal, ### para secciones).\n"
            f"2. Utiliza blockquotes (>) para destacar ideas clave o resúmenes breves.\n"
            f"3. Emplea viñetas ordenadas (▸) y separadores limpios (━━━━━━━━━━━━━━━━━━━━━).\n"
            f"4. Añade un pie sutil al final con la etiqueta '-#'.\n"
            f"5. NO uses bloques de código con ``` para el texto, déjalo libre en Markdown legible.\n"
            f"6. NO añadas introducciones como 'Aquí tienes el anuncio:'. Devuelve ÚNICAMENTE el texto final formateado listo para publicar."
        )

        redaccion_ia = await preguntar_ia(prompt)

        # Si la IA falla por red, usamos el borrador original con maquetación de respaldo
        if redaccion_ia.startswith("❌") or redaccion_ia.startswith("⚠️"):
            comunicado = (
                f"# 📢 {titulo.upper()}\n"
                f"> **Publicado por la Administración**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{mensaje}\n\n"
                f"-# Comunicado oficial de {ctx.guild.name}"
            )
        else:
            comunicado = redaccion_ia

        # Manejo de la mención
        prefijo_mencion = ""
        if mencion == "everyone":
            prefijo_mencion = "@everyone\n\n"
        elif mencion == "here":
            prefijo_mencion = "@here\n\n"

        # Publicar en el canal destino
        await canal.send(f"{prefijo_mencion}{comunicado}")
        await ctx.send(f"✨ **Comunicado publicado exitosamente en {canal.mention}.**", ephemeral=True)

    # ─────────────────────────────────────────────────────────────
    #  SAY LIMPIO
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="say", description="Transmite un mensaje directo en el canal")
    @app_commands.describe(mensaje="Mensaje a enviar")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, mensaje: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.channel.send(mensaje)

    # ─────────────────────────────────────────────────────────────
    #  POLL INTERACTIVO
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="poll", description="Crea una consulta comunitaria con botones en tiempo real")
    @app_commands.describe(pregunta="Tema a someter a votación")
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, pregunta: str):
        await ctx.defer()
        cuerpo = (
            f"## 📊 CONSULTA A LA COMUNIDAD\n"
            f"> **Propuesta:** {pregunta}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Pulsa los botones inferiores para emitir o revocar tu postura.*"
        )
        view = PollView(pregunta)
        await ctx.send(cuerpo, view=view)

    # ─────────────────────────────────────────────────────────────
    #  RECORDATORIO (REMIND)
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="remind", description="Fija un recordatorio con aviso sonoro/mención")
    @app_commands.describe(minutos="Minutos para el aviso", recordatorio="Motivo de la alerta")
    async def remind(self, ctx, minutos: int, *, recordatorio: str):
        await ctx.defer(ephemeral=True)
        if minutos <= 0:
            return await ctx.send("⚠️ El tiempo debe ser superior a 0 minutos.", ephemeral=True)

        await ctx.send(f"⏳ **Recordatorio programado:** Te avisaré en `{minutos}` min sobre *\"{recordatorio}\"*.", ephemeral=True)
        await asyncio.sleep(minutos * 60)
        await ctx.channel.send(
            f"⏰ {ctx.author.mention}\n"
            f"> 🔔 **RECORDATORIO PROGRAMADO:**\n"
            f"> *{recordatorio}*\n"
            f"-# Alarma fijada hace {minutos} minutos."
        )

    # ─────────────────────────────────────────────────────────────
    #  SNIPE (RECUPERADOR DE MENSAJES BORRADOS)
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="snipe", description="Recupera la última transmisión borrada en este canal")
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        await ctx.defer()
        data = SNIPE_CACHE.get(ctx.channel.id)
        if not data:
            return await ctx.send("💬 **No hay mensajes borrados recientemente en este canal.**")

        contenido = data["contenido"] or "*[Mensaje sin texto o archivo puro]*"
        salida = (
            f"### 🎯 Mensaje Interceptado (Snipe)\n"
            f"> **Autor:** {data['autor'].mention} `[{data['autor'].name}]`\n"
            f"> **Eliminado:** <t:{int(data['hora'].timestamp())}:R>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{contenido}"
        )
        if data["adjunto"]:
            salida += f"\n\n📎 **Archivo adjunto:** {data['adjunto']}"

        await ctx.send(salida)

    # ─────────────────────────────────────────────────────────────
    #  TABLA DE ACTIVIDAD DE MODERADORES
    # ─────────────────────────────────────────────────────────────
    @commands.hybrid_command(name="staff-activity", description="Genera una tabla de intervenciones del equipo de moderación")
    @commands.has_permissions(administrator=True)
    async def staff_activity(self, ctx):
        await ctx.defer()
        cases = cargar_cases()
        conteo = {}
        for c in cases.values():
            mod = c.get("moderador_id")
            if mod:
                conteo[mod] = conteo.get(mod, 0) + 1

        if not conteo:
            return await ctx.send("📋 *No se registran intervenciones disciplinarias en el historial.*")

        ordenados = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        lineas = []
        for i, (mid, total) in enumerate(ordenados[:10], 1):
            lineas.append(f"`#{i:02d}` <@{mid}> ▸ **{total}** intervenciones registradas")

        reporte = (
            f"# 🏆 RENDIMIENTO DE MODERACIÓN // {ctx.guild.name.upper()}\n"
            f"> Evaluando intervenciones históricas del equipo de moderación.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(lineas) +
            f"\n\n-# Registro actualizado de {ctx.guild.name} • Elixyr Security"
        )
        await ctx.send(reporte)


async def setup(bot):
    await bot.add_cog(Utilidades(bot))