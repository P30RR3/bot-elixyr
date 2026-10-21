"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // ADVANCED UTILITIES & EDITORIAL TOOLS (NEW GEN v6.0)
  Capacidades: Redacción Editorial con IA (LiveAction), Encuestas Dinámicas,
               Radar Snipe con Memoria Protegida y Tabla de Rendimiento Staff
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import inspect
from datetime import datetime, timezone
from collections import OrderedDict
from utils.helpers import cargar_cases
from utils.ia import preguntar_ia
from utils.ui import formato_editorial, barra_progreso, LiveActionController

# Snipe Cache con desalojo acotado para prevenir consumo indebido de RAM
MAX_SNIPE_CANALES = 100
SNIPE_BUFFER = OrderedDict()

async def _ejecutar_helper(func, *args, **kwargs):
    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return await res
    return res

class PollView(discord.ui.View):
    def __init__(self, pregunta: str):
        super().__init__(timeout=None)
        self.pregunta = pregunta
        self.a_favor = set()
        self.en_contra = set()

    def _actualizar_panel(self) -> str:
        total = len(self.a_favor) + len(self.en_contra)
        pct_si = int((len(self.a_favor) / total) * 100) if total > 0 else 0
        pct_no = int((len(self.en_contra) / total) * 100) if total > 0 else 0

        return (
            f"> **Propuesta:** *\"{self.pregunta}\"*\n"
            f"> **Participación:** `{total}` votos registrados\n\n"
            f"👍 **A Favor:** {barra_progreso(len(self.a_favor), total if total > 0 else 1)} `{pct_si}%` ({len(self.a_favor)})\n"
            f"👎 **En Contra:** {barra_progreso(len(self.en_contra), total if total > 0 else 1)} `{pct_no}%` ({len(self.en_contra)})\n\n"
            f"-# Utiliza los botones inferiores para emitir o revocar tu voto."
        )

    @discord.ui.button(label="A Favor", style=discord.ButtonStyle.success, emoji="👍", custom_id="poll_vote_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        self.en_contra.discard(uid)
        if uid in self.a_favor:
            self.a_favor.remove(uid)
        else:
            self.a_favor.add(uid)

        panel = formato_editorial("CONSULTA DEMOCRÁTICA // COMUNIDAD", self._actualizar_panel(), badge="POLL-TERMINAL")
        await interaction.response.edit_message(content=panel, view=self)

    @discord.ui.button(label="En Contra", style=discord.ButtonStyle.danger, emoji="👎", custom_id="poll_vote_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        self.a_favor.discard(uid)
        if uid in self.en_contra:
            self.en_contra.remove(uid)
        else:
            self.en_contra.add(uid)

        panel = formato_editorial("CONSULTA DEMOCRÁTICA // COMUNIDAD", self._actualizar_panel(), badge="POLL-TERMINAL")
        await interaction.response.edit_message(content=panel, view=self)

class Utilidades(commands.Cog):
    """Herramientas tácticas, encuestas interactivas, anuncios de alta gama y utilidades."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        SNIPE_BUFFER[message.channel.id] = {
            "autor": message.author,
            "contenido": message.content or "*[Sin texto / Solo archivo]*",
            "adjunto": message.attachments[0].url if message.attachments else None,
            "hora": datetime.now(timezone.utc)
        }
        SNIPE_BUFFER.move_to_end(message.channel.id)

        if len(SNIPE_BUFFER) > MAX_SNIPE_CANALES:
            SNIPE_BUFFER.popitem(last=False)

    # ═════════════════════════════════════════════════════════════
    #  1. COMUNICADOS EDITORIALES CON IA (ANNOUNCE)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="announce", description="La IA toma tu borrador y lo convierte en un comunicado formal con diseño gráfico Markdown")
    @app_commands.describe(
        canal="Canal donde se publicará la transmisión",
        titulo="Asunto o encabezado del comunicado",
        mensaje="Borrador simple con las ideas a transmitir",
        estilo="Tono de redacción táctico",
        mencion="Mención perimetral de audiencia"
    )
    @app_commands.choices(
        estilo=[
            app_commands.Choice(name="Formal y Ejecutivo", value="formal"),
            app_commands.Choice(name="Militar / Cyberpunk Táctico", value="tactico"),
            app_commands.Choice(name="Alerta Crítica / Seguridad", value="alerta"),
            app_commands.Choice(name="Cálido y Comunitario", value="amigable")
        ],
        mencion=[
            app_commands.Choice(name="Sin Mención", value="none"),
            app_commands.Choice(name="@everyone", value="everyone"),
            app_commands.Choice(name="@here", value="here")
        ]
    )
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx, canal: discord.TextChannel, titulo: str, *, mensaje: str, estilo: str = "formal", mencion: str = "none"):
        await ctx.defer(ephemeral=True)

        live = LiveActionController(ctx, "Maquetación Editorial // Comunicado IA", total_pasos=2)
        await live.iniciar()

        await live.actualizar("Estructurando redacción y maquetando sintaxis visual...", exito=True)

        prompt = (
            f"Eres un diseñador gráfico editorial y redactor oficial de una organización de ciberseguridad.\n"
            f"Transforma este borrador simple en un comunicado visualmente impactante, pulcro y elegante.\n\n"
            f"Título: '{titulo}'\n"
            f"Estilo: '{estilo}'\n"
            f"Borrador original: \"{mensaje}\"\n\n"
            f"Reglas estrictas de maquetación:\n"
            f"1. Utiliza encabezados (# y ###).\n"
            f"2. Utiliza blockquotes (>) para conceptos clave y viñetas (▸).\n"
            f"3. Utiliza separadores limpios (━━━━━━━━━━━━━━━━━━━━━).\n"
            f"4. Agrega un sutil pie con '-#'.\n"
            f"5. Devuelve ÚNICAMENTE el texto final formateado, sin comentarios introductorios."
        )

        redaccion = await preguntar_ia(prompt, max_tokens=600)
        await live.finalizar("Comunicado compilado y publicado.", error=False)

        prefijo = ""
        if mencion == "everyone":
            prefijo = "@everyone\n\n"
        elif mencion == "here":
            prefijo = "@here\n\n"

        comunicado_final = redaccion if not redaccion.startswith("❌") else f"# 📢 {titulo.upper()}\n\n{mensaje}"
        await canal.send(f"{prefijo}{comunicado_final}")
        await ctx.send(f"✨ **Comunicado despachado exitosamente en {canal.mention}.**", ephemeral=True)

    # ═════════════════════════════════════════════════════════════
    #  2. CONSULTA COMUNITARIA EN TIEMPO REAL (POLL)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="poll", description="Crea una votación comunitaria en tiempo real con barras dinámicas")
    @app_commands.describe(pregunta="Pregunta o propuesta a someter a votación")
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, pregunta: str):
        await ctx.defer()
        view = PollView(pregunta)
        panel = formato_editorial("CONSULTA DEMOCRÁTICA // COMUNIDAD", view._actualizar_panel(), badge="POLL-TERMINAL")
        await ctx.send(panel, view=view)

    # ═════════════════════════════════════════════════════════════
    #  3. RADAR DE INTERCEPCIÓN (SNIPE)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="snipe", description="Recupera el último mensaje destruido en este canal")
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        await ctx.defer()
        data = SNIPE_BUFFER.get(ctx.channel.id)
        if not data:
            return await ctx.send("💬 **No hay transmisiones destruidas recientemente en este sector.**", ephemeral=True)

        marca_t = int(data["hora"].timestamp())
        cuerpo = (
            f"> **Autor Original:** {data['autor'].mention} (`{data['autor'].id}`)\n"
            f"> **Destruido:** <t:{marca_t}:R>\n\n"
            f"**Contenido Capturado:**\n"
            f"```{data['contenido']}```"
        )
        if data["adjunto"]:
            cuerpo += f"\n📎 **Archivo Anexo:** {data['adjunto']}"

        await ctx.send(formato_editorial("TRANSMISIÓN INTERCEPTADA // SNIPE", cuerpo, badge="SIGNAL-RECOVERY"))

    # ═════════════════════════════════════════════════════════════
    #  4. TRANSMISIÓN DIRECTA (SAY) Y RECORDATORIO (REMIND)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="say", description="Transmite un comunicado directo a través de la identidad del bot")
    @app_commands.describe(mensaje="Contenido de la transmisión")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, mensaje: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.channel.send(mensaje)

    @commands.hybrid_command(name="remind", description="Programa una alarma de recordatorio con notificación táctica")
    @app_commands.describe(minutos="Minutos de espera", recordatorio="Motivo de la alarma")
    async def remind(self, ctx, minutos: int, *, recordatorio: str):
        await ctx.defer(ephemeral=True)
        if minutos <= 0:
            return await ctx.send("⚠️ El tiempo debe ser mayor a 0 minutos.", ephemeral=True)

        await ctx.send(f"⏳ **Recordatorio fijado:** Te notificaré en `{minutos}m` sobre *\"{recordatorio}\"*.", ephemeral=True)
        await asyncio.sleep(minutos * 60)

        aviso = (
            f"⏰ {ctx.author.mention}\n"
            f"> **Alerta Programada Cumplida:**\n"
            f"> *{recordatorio}*\n"
            f"-# Temporizador fijado hace {minutos} minutos."
        )
        await ctx.channel.send(aviso)

    # ═════════════════════════════════════════════════════════════
    #  5. TABLA DE RENDIMIENTO STAFF
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="staff-activity", description="Genera el reporte de intervenciones disciplinarias del equipo de moderación")
    @commands.has_permissions(administrator=True)
    async def staff_activity(self, ctx):
        await ctx.defer()
        cases = await _ejecutar_helper(cargar_cases)

        conteo = {}
        for c in cases.values():
            mid = c.get("moderador_id")
            if mid:
                conteo[mid] = conteo.get(mid, 0) + 1

        if not conteo:
            return await ctx.send("📋 *No se registran expedientes disciplinarios en la base de datos central.*")

        ordenados = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        lineas = [f"`#{i:02d}` <@{mid}> ▸ **{total}** intervenciones registradas" for i, (mid, total) in enumerate(ordenados[:10], 1)]

        cuerpo = (
            f"> **Evaluación de Actividad Disciplinaria // {ctx.guild.name}**\n\n"
            + "\n".join(lineas) +
            f"\n\n-# Métricas extraídas de la bóveda SQLite del SOC."
        )
        await ctx.send(formato_editorial("RENDIMIENTO DE MODERACIÓN", cuerpo, badge="STAFF-METRICS"))


async def setup(bot):
    await bot.add_cog(Utilidades(bot))