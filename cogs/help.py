import discord
from discord.ext import commands
from discord import app_commands
import time

SECCIONES = {
    "inicio": (
        "# 🛡️ TERMINAL OPERATIVA // ELIXYR SOC\n"
        "> **Plataforma central de ciberseguridad, gestión y soporte con IA.**\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "👋 Bienvenido al centro de control.\n\n"
        "📂 **Selecciona una división en el menú inferior** para ver los comandos disponibles.\n\n"
        "-# Elixyr Sentinel SOC • Motor Neuronal Activo"
    ),
    "defensa": (
        "### 🚨 DIVISIÓN DE DEFENSA & ANTI-RAID\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/antiraid` — Filtro perimetral contra oleadas de bots.\n"
        "▸ `/antinuke` — Centinela anti-sabotaje (protege canales y roles).\n"
        "▸ `/server-audit` — Escaneo profundo de vulnerabilidades (Red Team Pentest).\n"
        "▸ `/automod` • `/automod-ia` — Firewall de chat con Shadow Flagging.\n"
    ),
    "moderacion": (
        "### ⚖️ DIVISIÓN DISCIPLINARIA\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/ban` • `/unban` — Exclusión permanente y revocación.\n"
        "▸ `/kick` — Expulsión con notificación IA.\n"
        "▸ `/mute` • `/unmute` — Aislamiento temporal.\n"
        "▸ `/warn` • `/warnings` • `/clearwarns` — Sistema de advertencias.\n"
        "▸ `/purge` • `/purge-ia` — Limpieza numérica o purga selectiva de toxicidad con IA.\n"
    ),
    "gestion": (
        "### 🛠️ INFRAESTRUCTURA Y ROLES\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/role-create-ia` — **[IA]** Forja roles configurando permisos, color y jerarquía.\n"
        "▸ `/channel-create-ia` — **[IA]** Diseña canales con nombre, tipo y topic automático.\n"
        "▸ `/lock` • `/unlock` — Pausa la transmisión en el canal.\n"
        "▸ `/lock-all` • `/unlock-all` — Bloqueo masivo de canales.\n"
        "▸ `/nuke-channel` — Clona y destruye el canal actual.\n"
        "▸ `/strip-roles` — Botón de pánico: Despoja de roles a una cuenta hackeada.\n"
        "▸ `/role-all` • `/role-bots` — Asignación masiva.\n"
    ),
    "ia": (
        "### 🧠 NÚCLEO COGNITIVO (IA)\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/edit` — Genera o edita imágenes con IA.\n"
        "▸ `/ask` — Interacción libre con Cerebras AI (con memoria).\n"
        "▸ `/ia-analyze-chat` — Mide el Índice de Hostilidad del canal.\n"
        "▸ `/ia-sentiment` — Perfilado psicológico de un usuario.\n"
        "▸ `/ia-detect-phishing` — Análisis forense de enlaces maliciosos.\n"
        "▸ `/ia-rule-check` — Tribunal arbitral IA para casos hipotéticos.\n"
    ),
    "soporte": (
        "### 📁 CENTRO SOC & EXPEDIENTES\n"
        "✦ ────────────────────────────────────────── ✦\n"
        "▸ `/setup-logs` — Enruta eventos críticos al canal SOC.\n"
        "▸ `/case` • `/delcase` — Consulta expedientes disciplinarios.\n"
        "▸ `/historial` • `/expediente-ia` — Dossier judicial con perfilado conductual.\n"
        "▸ `/userinfo` — Radiografía de cuenta y nivel de riesgo.\n"
        "▸ `/ticket-panel` • `/setup-tickets` — Mesa de ayuda con triaje IA.\n"
    )
}

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Centro de Control", emoji="🛡️", value="inicio"),
            discord.SelectOption(label="Defensa & Anti-Raid", emoji="🚨", value="defensa"),
            discord.SelectOption(label="Moderación & Sanciones", emoji="⚖️", value="moderacion"),
            discord.SelectOption(label="Infraestructura & Roles", emoji="🛠️", value="gestion"),
            discord.SelectOption(label="IA & Análisis", emoji="🧠", value="ia"),
            discord.SelectOption(label="SOC & Expedientes", emoji="📁", value="soporte"),
        ]
        super().__init__(placeholder="📂 Selecciona una división...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=SECCIONES.get(self.values[0], SECCIONES["inicio"]))

class HelpNavView(discord.ui.View):
    def __init__(self, autor):
        super().__init__(timeout=120)
        self.autor = autor
        self.add_item(HelpDropdown())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("❌ Usa `/help` para abrir tu propio panel.", ephemeral=True)
            return False
        return True

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Muestra el menú interactivo de comandos")
    async def help_cmd(self, ctx):
        await ctx.defer()
        await ctx.send(content=SECCIONES["inicio"], view=HelpNavView(ctx.author))

    @commands.hybrid_command(name="ping", description="Mide la latencia del Gateway y la API")
    async def ping(self, ctx):
        t1 = time.perf_counter()
        msg = await ctx.send("📡 *Calculando telemetría...*")
        lat_api = round((time.perf_counter() - t1) * 1000)
        await msg.edit(content=f"📡 **Telemetría:** Gateway `{round(self.bot.latency * 1000)}ms` | API `{lat_api}ms`")

async def setup(bot):
    await bot.add_cog(Help(bot))