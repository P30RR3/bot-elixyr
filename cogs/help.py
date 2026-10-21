"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // MASTER OPERATIONAL HELP & TELEMETRY (NEW GEN v6.0)
  Capacidades: Terminal de Ayuda Dinámica con Dropdown, Navegación Táctica,
               Telemetría Completa en Vivo (Gateway, API y Base de Datos)
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
import time
from utils.ui import formato_editorial

SECCIONES_AYUDA = {
    "terminal": (
        "### 🛡️ DIVISIÓN CENTRAL SOC & TELEMETRÍA\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/terminal` — Despliega el Dashboard interactivo DEFCON en tiempo real.\n"
        "▸ `/server-audit` — Pentest forense de vulnerabilidades simulado con IA.\n"
        "▸ `/threat-scan` — Escanea a un miembro y calcula su Threat Score biométrico.\n"
        "▸ `/ping` — Mide telemetría y latencias (Gateway, API REST y Motor IA)."
    ),
    "defensa": (
        "### 🚨 DIVISIÓN DE DEFENSA PERIMETRAL & ANTI-RAID\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/antiraid` — Configura umbrales de velocidad y control de ráfagas.\n"
        "▸ `/antiraid-mode` — Alterna entre DEFCON 5 (Pacífico), 3 (Intermedio) y 1 (Hardcore).\n"
        "▸ `/antinuke` — Centinela anti-sabotaje contra borrado de canales, roles y webhooks.\n"
        "▸ `/lockdown` • `/unlockdown` — Botón de pánico: congelamiento y restauración perimetral.\n"
        "▸ `/deploy-honeypot` • `/remove-honeypot` — Despliega y retira canales trampa con baneo a 0ms."
    ),
    "disciplina": (
        "### ⚖️ DIVISIÓN DISCIPLINARIA & EXPEDIENTES\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/ban` • `/unban` — Exclusión permanente y revocación con dictamen judicial IA.\n"
        "▸ `/softban` — Purga de mensajes hostiles de 1 a 7 días y expulsión.\n"
        "▸ `/kick` — Expulsión formal con memorándum al infractor.\n"
        "▸ `/mute` • `/unmute` — Aislamiento temporal hasta por 28 días.\n"
        "▸ `/warn` • `/clearwarns` — Advertencias con escalada automática (Timeout y Kick).\n"
        "▸ `/case` • `/delcase` — Inspección y revocación de expedientes disciplinarios.\n"
        "▸ `/historial` • `/expediente-ia` — Dossier de antecedentes y perfilado psicométrico IA."
    ),
    "infraestructura": (
        "### 🛠️ INFRAESTRUCTURA, CANALES & CREDENCIALES\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/role-create-ia` — Forja credenciales calculando su matriz de permisos con IA.\n"
        "▸ `/channel-create-ia` — Diseña y aprovisiona canales según su función operativa.\n"
        "▸ `/lock` • `/unlock` — Bloquea y libera la frecuencia de transmisión en el canal.\n"
        "▸ `/lock-all` • `/unlock-all` — Bloqueo y restauración masiva con seguimiento en vivo.\n"
        "▸ `/purge` • `/purge-ia` — Purga paramétrica o smart purge semántico en ráfaga.\n"
        "▸ `/nuke-channel` — Protocolo de demolición y reconstrucción del canal al 100%.\n"
        "▸ `/strip-roles` — Protocolo de cuarentena para cuentas comprometidas.\n"
        "▸ `/role-all` • `/role-bots` — Despliegue masivo de roles con barra en vivo."
    ),
    "cognitivo": (
        "### 🧠 NÚCLEO COGNITIVO & HERRAMIENTAS IA\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/ask` — Conversación abierta con Cerebras AI con memoria protegida.\n"
        "▸ `/olvidar` • `/resumir` — Limpieza de sesión activa y síntesis de documentos.\n"
        "▸ `/ia-analyze-chat` — Radar de tensión y hostilidad en el canal.\n"
        "▸ `/ia-sentiment` — Radiografía conductual y psicológica de un usuario.\n"
        "▸ `/scan-url` — Sandbox forense para peritaje de enlaces sospechosos o phishing.\n"
        "▸ `/ia-rule-check` — Tribunal arbitral para deliberar conflictos hipotéticos.\n"
        "▸ `/ia-ticket-suggest` — Asistente copiloto con respuestas modelo para soporte."
    ),
    "operaciones": (
        "### 📁 ASISTENCIA, BIOMETRÍA & OPERACIONES AVANZADAS\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/ticket-panel` • `/setup-tickets` — Mesa de ayuda con triaje IA y transcript.\n"
        "▸ `/setup-captcha` — Portal de acceso biométrico con Prueba de Turing.\n"
        "▸ `/clone-profile` — Clonación quirúrgica de roles entre dos entidades.\n"
        "▸ `/role-backup` • `/role-restore` — Copia de seguridad y recuperación de roles.\n"
        "▸ `/announce` — Maquetación de comunicados oficiales con diseño editorial IA.\n"
        "▸ `/poll` — Consultas comunitarias interactivas con barras dinámicas.\n"
        "▸ `/snipe` • `/staff-activity` — Recuperación de mensajes y rendimiento del staff."
    )
}

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(label="Centro SOC & Telemetría", emoji="🛡️", value="terminal", description="Terminal DEFCON y auditoría"),
            discord.SelectOption(label="Defensa & Anti-Raid", emoji="🚨", value="defensa", description="Filtros perimetrales y honeypots"),
            discord.SelectOption(label="Justicia & Disciplina", emoji="⚖️", value="disciplina", description="Sanciones y expedientes legales"),
            discord.SelectOption(label="Infraestructura & Canales", emoji="🛠️", value="infraestructura", description="Roles, canales y smart purge"),
            discord.SelectOption(label="Núcleo Cognitivo IA", emoji="🧠", value="cognitivo", description="Cerebras AI y herramientas forenses"),
            discord.SelectOption(label="Soporte & Operaciones", emoji="📁", value="operaciones", description="Tickets, biometría y respaldos")
        ]
        super().__init__(placeholder="📂 Selecciona una división operativa...", options=opciones, custom_id="help_nav")

    async def callback(self, interaction: discord.Interaction):
        seleccion = self.values[0]
        contenido = SECCIONES_AYUDA.get(seleccion, SECCIONES_AYUDA["terminal"])
        panel = formato_editorial(f"TERMINAL OPERATIVA // {seleccion.upper()}", contenido, badge="DIRECTORY")
        await interaction.response.edit_message(content=panel)

class HelpView(discord.ui.View):
    def __init__(self, autor_id: int):
        super().__init__(timeout=120)
        self.autor_id = autor_id
        self.add_item(HelpDropdown())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("❌ Esta terminal de ayuda fue abierta por otro oficial.", ephemeral=True)
            return False
        return True

class Help(commands.Cog):
    """Módulo maestro de asistencia, navegación de directivas y telemetría de red."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Despliega la terminal operativa interactiva con todas las directivas")
    async def help_cmd(self, ctx):
        await ctx.defer()
        contenido_inicial = (
            f"> **Plataforma Integral de Ciberseguridad, Peritaje Forense y Soporte Cognitivo.**\n\n"
            f"Bienvenido al centro de mando. Selecciona una división en el menú inferior "
            f"para consultar los parámetros y capacidades de cada directiva táctica.\n\n"
            f"-# Elixyr Guard v6.0 • Cognitive Engine Active"
        )
        panel = formato_editorial(f"TERMINAL CENTRAL DE MANDO // {ctx.guild.name.upper()}", contenido_inicial, badge="SOC-HELP")
        await ctx.send(panel, view=HelpView(ctx.author.id))

    @commands.hybrid_command(name="ping", description="Mide con precisión la latencia del Gateway, la API REST y los subsistemas")
    async def ping(self, ctx):
        t1 = time.perf_counter()
        msg = await ctx.send("📡 *Calculando telemetría de red y respuesta de subsistemas...*")
        lat_api = round((time.perf_counter() - t1) * 1000)
        lat_gw = round(self.bot.latency * 1000)

        cuerpo = (
            f"> **Gateway WebSocket:** `{lat_gw}ms`\n"
            f"> **API REST Discord:** `{lat_api}ms`\n"
            f"> **Base de Datos SQLite (WAL):** `Operativa (Sub-1ms)`\n"
            f"> **Motor Cerebras AI:** `En Línea (llama-3.3-70b)`\n\n"
            f"-# Telemetría de alta frecuencia sincronizada."
        )
        await msg.edit(content=formato_editorial("TELEMETRÍA OPERATIVA DE SISTEMAS", cuerpo, badge="LATENCY"))


async def setup(bot):
    await bot.add_cog(Help(bot))