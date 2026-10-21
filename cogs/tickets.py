"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // AI TICKET DESK & FORENSIC TRANSCRIPTS (NEW GEN v6.0)
  Capacidades: Triaje Preliminar con Cerebras AI, Reclamación Táctica de Casos,
               Resumen Ejecutivo de Resolución y Transcripción Forense en Archivo
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import io
import asyncio
import logging
from datetime import datetime, timezone
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ia import preguntar_ia
from utils.ui import formato_editorial

logger = logging.getLogger("ElixyrTickets")

CATEGORIAS_SOPORTE = [
    ("🛡️ Seguridad & Reportes", "Denuncias sobre infracciones, phishing o ataques"),
    ("💎 Membresías & Roles", "Consultas sobre jerarquía, accesos o suscripciones"),
    ("🔧 Asistencia Técnica", "Problemas técnicos con el servidor o el bot"),
    ("💡 Propuestas & Feedback", "Sugerencias operativas para la administración"),
    ("📩 Atención General", "Consultas privadas generales")
]

class TicketModal(discord.ui.Modal, title="Apertura de Expediente"):
    asunto = discord.ui.TextInput(
        label="Asunto de la Consulta",
        placeholder="Ej: Reporte de usuario sospechoso / Problema con rol...",
        required=True,
        max_length=100
    )
    descripcion = discord.ui.TextInput(
        label="Detalles del Caso",
        placeholder="Describe detalladamente la situación para que la IA y el Staff puedan evaluarla...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    def __init__(self, categoria: str):
        super().__init__()
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        cfg = obtener_guild_config(guild.id)
        cat_id = cfg.get("ticket_category")
        staff_id = cfg.get("staff_role")

        cat_canal = guild.get_channel(int(cat_id)) if cat_id else None
        staff_rol = guild.get_role(int(staff_id)) if staff_id else None

        if not cat_canal or not staff_rol:
            return await interaction.followup.send(
                "⚠️ **Error de Infraestructura:** El sistema de tickets no ha sido aprovisionado (`/setup-tickets`).",
                ephemeral=True
            )

        # Configurar permisos estrictos (Zero-Trust)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            ),
            staff_rol: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        nombre_canal = f"tkt-{user.name[:12]}-{user.discriminator if user.discriminator != '0' else str(user.id)[-4:]}"
        canal = await guild.create_text_channel(
            name=nombre_canal,
            category=cat_canal,
            overwrites=overwrites,
            topic=f"Expediente SOC ▸ Titular: {user.id} ▸ Área: {self.categoria}"
        )

        # ─── TRIAJE INMEDIATO ASISTIDO POR IA ───
        prompt_triaje = (
            f"Actúa como el asistente virtual de primer contacto (Nivel 1) del SOC.\n"
            f"Área: '{self.categoria}' | Asunto: '{self.asunto.value}'\n"
            f"Problema expuesto: '{self.descripcion.value}'\n"
            f"Escribe un mensaje de 2 líneas, empático y profesional, indicando qué datos o evidencias "
            f"puede ir preparando el usuario mientras un oficial asume el mando. Sin saludos largos."
        )
        triaje_ia = await preguntar_ia(prompt_triaje, max_tokens=100)
        if triaje_ia.startswith("❌") or triaje_ia.startswith("⚠️"):
            triaje_ia = "Un oficial del departamento ha sido alertado y tomará la conexión en breve."

        cuerpo_ticket = (
            f"> **Titular:** {user.mention} (`{user.id}`)\n"
            f"> **División:** `{self.categoria}`\n"
            f"> **Asunto:** {self.asunto.value}\n\n"
            f"**Exposición del Caso:**\n"
            f"```{self.descripcion.value}```\n\n"
            f"**🧠 Triaje Inicial (Cerebras AI):**\n"
            f"> *{triaje_ia}*\n\n"
            f"-# 📢 {staff_rol.mention} ▸ Reclamar el caso con los controles inferiores."
        )

        view = TicketControlView(user.id, self.categoria, self.asunto.value)
        panel = formato_editorial(f"EXPEDIENTE DE SOPORTE // #{canal.name}", cuerpo_ticket, badge="HELPDESK-SOC")
        await canal.send(panel, view=view)
        await interaction.followup.send(f"✦ **Expediente generado exitosamente:** Dirígete a {canal.mention}", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self, titular_id: int, categoria: str, asunto: str):
        super().__init__(timeout=None)
        self.titular_id = titular_id
        self.categoria = categoria
        self.asunto = asunto
        self.oficial_asignado = None

    @discord.ui.button(label="Reclamar Expediente", style=discord.ButtonStyle.primary, emoji="🙋‍♂️", custom_id="claim_ticket")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.oficial_asignado:
            return await interaction.response.send_message(f"⚠️ Este expediente ya está a cargo de <@{self.oficial_asignado}>.", ephemeral=True)

        self.oficial_asignado = interaction.user.id
        button.disabled = True
        button.label = f"A cargo de {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🛡️ {interaction.user.mention} ha tomado la dirección de este caso.")

    @discord.ui.button(label="Clausurar y Auditar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CerrarTicketModal(self.titular_id, self.categoria, self.asunto))

class CerrarTicketModal(discord.ui.Modal, title="Resolución y Cierre"):
    resolucion = discord.ui.TextInput(
        label="Resolución del Caso",
        placeholder="Resume brevemente la solución brindada o el motivo del cierre...",
        required=True,
        max_length=300
    )

    def __init__(self, titular_id: int, categoria: str, asunto: str):
        super().__init__()
        self.titular_id = titular_id
        self.categoria = categoria
        self.asunto = asunto

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        canal = interaction.channel
        guild = interaction.guild

        # 1. Compilación de Transcripción Completa
        mensajes_log = []
        async for m in canal.history(limit=150, oldest_first=True):
            marca = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            mensajes_log.append(f"[{marca}] {m.author.name} ({m.author.id}): {m.content}")

        transcripcion_raw = "\n".join(mensajes_log)

        # 2. Resumen Ejecutivo con Cerebras AI
        prompt_resumen = (
            f"Actúa como supervisor de calidad y auditor forense.\n"
            f"Ticket: '{self.asunto}' | Cierre: '{self.resolucion.value}'\n"
            f"Transcripción parcial:\n{transcripcion_raw[-1500:]}\n\n"
            f"Genera un informe ejecutivo de 2 líneas resumiendo el incidente y la resolución adoptada."
        )
        resumen_ia = await preguntar_ia(prompt_resumen, max_tokens=100)

        # 3. Archivo Forense Adjunto
        buffer = io.BytesIO(transcripcion_raw.encode("utf-8"))
        archivo_adjunto = discord.File(buffer, filename=f"transcript-{canal.name}.txt")

        # 4. Despacho a la Bóveda SOC
        cfg = obtener_guild_config(guild.id)
        log_id = cfg.get("ticket_log_channel") or cfg.get("audit_channel")
        if log_id:
            ch_log = guild.get_channel(int(log_id))
            if ch_log:
                dossier = (
                    f"> **Expediente:** `{canal.name}`\n"
                    f"> **Titular:** <@{self.titular_id}> (`{self.titular_id}`)\n"
                    f"> **Oficial de Cierre:** {interaction.user.mention}\n"
                    f"> **Resolución:** {self.resolucion.value}\n\n"
                    f"**🧠 Dictamen Ejecutivo (Cerebras AI):**\n"
                    f"> *{resumen_ia}*"
                )
                panel_log = formato_editorial("EXPEDIENTE CLAUSURADO & AUDITADO", dossier, badge="SOC-ARCHIVE")
                await ch_log.send(panel_log, file=archivo_adjunto)

        aviso = (
            f"### 🔒 EXPEDIENTE CLAUSURADO\n"
            f"> **Resolución:** {self.resolucion.value}\n"
            f"> *El sector se desintegrará en 5 segundos.*"
        )
        await canal.send(aviso)
        await asyncio.sleep(5)
        try:
            await canal.delete(reason=f"Ticket cerrado por {interaction.user}")
        except Exception:
            pass

class PanelTicketsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        opciones = [
            discord.SelectOption(label=cat, description=desc, value=cat)
            for cat, desc in CATEGORIAS_SOPORTE
        ]
        select = discord.ui.Select(
            placeholder="✦ Selecciona la división correspondiente...",
            options=opciones,
            custom_id="select_ticket_cat"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        cat = interaction.data["values"][0]
        await interaction.response.send_modal(TicketModal(cat))

class Tickets(commands.Cog):
    """Módulo de gestión de tickets, soporte técnico y triaje de seguridad."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket-panel", description="Despliega el centro de atención interactivo con triaje IA")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        await ctx.defer()
        contenido = (
            f"¿Requieres asistencia especializada, denunciar una vulnerabilidad o gestionar credenciales?\n\n"
            f"• *Despliega el menú inferior para abrir un canal privado y cifrado.*\n"
            f"• *Un motor de Inteligencia Artificial evaluará tu caso al instante para canalizarlo al personal correcto.*\n\n"
            f"-# Operaciones de soporte supervisadas por Elixyr Security Operations."
        )
        panel = formato_editorial(f"CENTRO DE ATENCIÓN Y SOPORTE // {ctx.guild.name.upper()}", contenido, badge="HELPDESK")
        await ctx.channel.send(panel, view=PanelTicketsView())
        await ctx.send("✦ **Panel de soporte desplegado exitosamente.**", ephemeral=True)

    @commands.hybrid_command(name="setup-tickets", description="Aprovisiona la categoría y el rol de staff para tickets")
    @app_commands.describe(
        categoria="Categoría donde se generarán los canales",
        rol_staff="Rol con autorización para atender casos",
        canal_logs="Canal para despachar transcripciones y cierres"
    )
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx, categoria: discord.CategoryChannel, rol_staff: discord.Role, canal_logs: discord.TextChannel = None):
        await ctx.defer()
        actualizar_guild_config(ctx.guild.id, "ticket_category", categoria.id)
        actualizar_guild_config(ctx.guild.id, "staff_role", rol_staff.id)
        if canal_logs:
            actualizar_guild_config(ctx.guild.id, "ticket_log_channel", canal_logs.id)

        desc = (
            f"> **Categoría Asignada:** `{categoria.name}`\n"
            f"> **División Staff:** {rol_staff.mention}\n"
            f"> **Canal de Transcripciones:** {canal_logs.mention if canal_logs else 'Bóveda SOC Principal'}"
        )
        await ctx.send(formato_editorial("CONFIGURACIÓN DE TICKETS APROBADA", desc, badge="SETUP-OK"))


async def setup(bot):
    await bot.add_cog(Tickets(bot))