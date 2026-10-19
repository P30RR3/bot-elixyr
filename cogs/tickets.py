import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import cargar_config, guardar_config
from utils.ia import preguntar_ia
import asyncio
import os
import json
from datetime import datetime, timezone

CONFIG = cargar_config()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKETS_FILE = os.path.join(BASE_DIR, "data", "tickets.json")

if not os.path.exists(TICKETS_FILE):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump({"contador": 0, "tickets": {}}, f, indent=2)

def cargar_tickets():
    with open(TICKETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_tickets(data):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

CATEGORIAS_TICKET = [
    ("🛡️ Seguridad & Reportes", "Denuncias sobre infracciones o ataques"),
    ("💎 Membresías & Roles", "Consultas de rango, VIP o accesos"),
    ("🔧 Soporte Técnico", "Problemas con el servidor o el bot"),
    ("💡 Sugerencias", "Propuestas de mejora para la administración"),
    ("📩 Atención General", "Cualquier otra consulta privada"),
]

class TicketModal(discord.ui.Modal, title="Apertura de Expediente de Soporte"):
    asunto = discord.ui.TextInput(
        label="Asunto o Motivo",
        placeholder="Ej: Reporte de usuario / Error en mi rol...",
        required=True,
        max_length=120,
    )
    descripcion = discord.ui.TextInput(
        label="Detalles de la Solicitud",
        placeholder="Explica detalladamente tu situación para que el Staff y la IA puedan evaluarlo...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500,
    )

    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        staff_role_id = CONFIG.get("staff_role")
        categoria_id = CONFIG.get("ticket_category")
        staff_role = guild.get_role(int(staff_role_id)) if staff_role_id else None
        categoria_canal = guild.get_channel(int(categoria_id)) if categoria_id else None

        if not staff_role or not categoria_canal:
            return await interaction.followup.send("⚠️ **Error de Infraestructura:** El sistema de tickets no está configurado (`/setup-tickets`).", ephemeral=True)

        data = cargar_tickets()
        data["contador"] += 1
        num_str = f"{data['contador']:04d}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }

        canal = await guild.create_text_channel(
            name=f"tkt-{num_str}-{user.name[:10]}",
            category=categoria_canal,
            overwrites=overwrites,
            topic=f"Expediente #{num_str} ▸ {user.id} ▸ {self.categoria}"
        )

        data["tickets"][str(canal.id)] = {
            "id": num_str,
            "usuario_id": str(user.id),
            "staff_id": None,
            "categoria": self.categoria,
            "asunto": self.asunto.value,
            "descripcion": self.descripcion.value,
            "estado": "abierto",
            "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        guardar_tickets(data)

        # ─── TRIAJE INMEDIATO CON IA ───
        prompt_triaje = (
            f"Eres el asistente virtual de soporte (Nivel 1) de un servidor de Discord.\n"
            f"Categoría del ticket: '{self.categoria}'\n"
            f"Asunto: '{self.asunto.value}'\n"
            f"Descripción: '{self.descripcion.value}'\n"
            f"Escribe un mensaje preliminar empático, profesional y conciso (máximo 3 líneas) indicándole al usuario qué datos adicionales "
            f"puede ir preparando mientras un oficial humano toma su caso. No uses saludos largos."
        )
        primer_auxilio_ia = await preguntar_ia(prompt_triaje)
        if primer_auxilio_ia.startswith("❌"):
            primer_auxilio_ia = "Un oficial de soporte ha sido notificado y se conectará a este canal en breve."

        mensaje_canal = (
            f"### 🎫 EXPEDIENTE DE SOPORTE `#{num_str}`\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Titular:** {user.mention} (`{user.id}`)\n"
            f"> **Categoría:** `{self.categoria}`\n"
            f"> **Asunto:** {self.asunto.value}\n\n"
            f"**Exposición del Caso:**\n"
            f"```{self.descripcion.value}```\n\n"
            f"**🧠 Triaje Preliminar (IA):**\n"
            f"> *{primer_auxilio_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"📢 {staff_role.mention} | Por favor, reclamar el ticket con el botón inferior."
        )

        view = TicketControlView()
        await canal.send(mensaje_canal, view=view)
        await interaction.followup.send(f"✦ **Expediente generado con éxito:** Dirígete a {canal.mention}", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Caso", style=discord.ButtonStyle.primary, emoji="🙋‍♂️", custom_id="claim_tkt")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = cargar_tickets()
        ticket = data["tickets"].get(str(interaction.channel.id))
        if not ticket:
            return await interaction.response.send_message("⚠️ Canal no identificado como ticket activo.", ephemeral=True)
        if ticket["staff_id"]:
            return await interaction.response.send_message(f"⚠️ Este caso ya fue reclamado por <@{ticket['staff_id']}>.", ephemeral=True)

        ticket["staff_id"] = str(interaction.user.id)
        guardar_tickets(data)

        button.disabled = True
        button.label = f"A cargo de {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🛡️ {interaction.user.mention} ha tomado la dirección de este caso. Por favor, espera sus instrucciones.")

    @discord.ui.button(label="Cerrar Expediente", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_tkt")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CerrarTicketModal())

class CerrarTicketModal(discord.ui.Modal, title="Finalizar Expediente"):
    motivo = discord.ui.TextInput(
        label="Resolución del Caso",
        placeholder="Describe brevemente la solución brindada...",
        required=True,
        max_length=300
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        canal = interaction.channel
        guild = interaction.guild

        data = cargar_tickets()
        ticket = data["tickets"].get(str(canal.id))
        if not ticket:
            return await interaction.followup.send("⚠️ No es un ticket registrado.")

        # Recopilar transcript para la IA
        mensajes = []
        async for m in canal.history(limit=100, oldest_first=True):
            if m.content:
                mensajes.append(f"[{m.author.name}]: {m.content}")

        transcripcion = "\n".join(mensajes)

        # ─── RESUMEN EJECUTIVO CON IA ───
        prompt_resumen = (
            f"Actúa como auditor de calidad de soporte. Lee esta transcripción de un ticket cerrado con la resolución '{self.motivo.value}':\n\n"
            f"{transcripcion[-1500:]}\n\n"
            f"Genera un informe de cierre de 2 líneas resumiendo el problema exacto que tuvo el usuario y cómo se resolvió. Sé formal y directo."
        )
        resumen_ia = await preguntar_ia(prompt_resumen)

        ticket["estado"] = "cerrado"
        guardar_tickets(data)

        aviso_cierre = (
            f"### 🔒 EXPEDIENTE EN PROCESO DE DESTRUCCIÓN\n"
            f"> **Clausurado por:** {interaction.user.mention}\n"
            f"> **Resolución:** {self.motivo.value}\n"
            f"> *El canal se eliminará en 5 segundos.*"
        )
        await canal.send(aviso_cierre)

        # Registro al canal de auditoría SOC
        log_ch_id = CONFIG.get("ticket_log_channel") or CONFIG.get("audit_channel")
        if log_ch_id:
            log_ch = guild.get_channel(int(log_ch_id))
            if log_ch:
                reporte_auditoria = (
                    f"### 📜 REPORTE DE TICKET CERRADO `#{ticket['id']}`\n"
                    f"✦ ────────────────────────────────────────── ✦\n"
                    f"> • **Usuario:** <@{ticket['usuario_id']}>\n"
                    f"> • **Atendido por:** {interaction.user.mention}\n"
                    f"> • **Categoría:** `{ticket['categoria']}`\n"
                    f"> • **Causa de Cierre:** {self.motivo.value}\n\n"
                    f"**Evaluación Ejecutiva (IA):**\n> *{resumen_ia}*\n"
                    f"✦ ────────────────────────────────────────── ✦"
                )
                await log_ch.send(reporte_auditoria)

        await asyncio.sleep(5)
        try: await canal.delete()
        except Exception: pass

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket-panel", description="Publica el panel interactivo de tickets")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        await ctx.defer()
        panel_texto = (
            f"# 💌 CENTRO DE ATENCIÓN Y ASISTENCIA TÁCTICA\n"
            f"✦ ────────────────────────────────────────── ✦\n\n"
            f"¿Requieres asistencia especializada, denunciar una infracción o gestionar tu membresía?\n\n"
            f"• *Haz clic en el menú inferior para desplegar tu canal privado.*\n"
            f"• *Un motor de Inteligencia Artificial evaluará tu caso al instante para agilizar tu respuesta.*\n\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        view = PanelDesplegableTickets()
        await ctx.channel.send(panel_texto, view=view)
        await ctx.send("✦ Panel de tickets desplegado.", ephemeral=True)

    @commands.hybrid_command(name="setup-tickets", description="Configura categoría y rol de staff para tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx, categoria: discord.CategoryChannel, staff_role: discord.Role, canal_logs: discord.TextChannel = None):
        await ctx.defer()
        CONFIG["ticket_category"] = categoria.id
        CONFIG["staff_role"] = staff_role.id
        if canal_logs: CONFIG["ticket_log_channel"] = canal_logs.id
        guardar_config(CONFIG)
        await ctx.send(f"✦ **[SISTEMA CONFIGURADO]** Categoría: `{categoria.name}` | Staff: {staff_role.mention}")

class PanelDesplegableTickets(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        opciones = [discord.SelectOption(label=cat, description=desc, value=cat) for cat, desc in CATEGORIAS_TICKET]
        select = discord.ui.Select(placeholder="✦ Selecciona el motivo de tu solicitud...", options=opciones, custom_id="ticket_menu")
        select.callback = self.menu_callback
        self.add_item(select)

    async def menu_callback(self, interaction: discord.Interaction):
        cat = interaction.data["values"][0]
        await interaction.response.send_modal(TicketModal(cat))

async def setup(bot):
    await bot.add_cog(Tickets(bot))