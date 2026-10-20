import discord
from datetime import datetime, timezone
from utils.helpers import cargar_config

CONFIG = cargar_config()

# ─────────────────────────────────────────────────────────────
#  PALETA DE COLORES "DARK SOC" (Optimizada para Modo Oscuro)
# ─────────────────────────────────────────────────────────────
PALETA = {
    "primario": 0x2B2D31,  # Gris oscuro nativo de Discord (Invisible embed)
    "exito":    0x00FF7F,  # Spring Green (Terminal)
    "error":    0xFF3131,  # Neon Red
    "alerta":   0xFFCC00,  # Cyber Yellow
    "info":     0x00E5FF,  # Cyan Neon
    "oscuro":   0x1E1F22,  # Background Discord
    "peligro":  0xFF0000,  # Nuke Red
}

FOOTER_TEXTO = "Elixyr Guard • Advanced Security Operations"

# ─────────────────────────────────────────────────────────────
#  HERRAMIENTAS VISUALES ÚNICAS (BARRAS DE ESTADO)
# ─────────────────────────────────────────────────────────────
def barra_riesgo(severidad: int) -> str:
    """Genera una barra de riesgo visual de 0 a 5 basada en IA."""
    cuadros_totales = 5
    llenos = min(max(severidad, 0), cuadros_totales)
    vacios = cuadros_totales - llenos
    barra = ("▰" * llenos) + ("▱" * vacios)
    porcentaje = (llenos / cuadros_totales) * 100
    return f"`[{barra}] {int(porcentaje)}% AMENAZA`"

def barra_progreso(actual: int, total: int, longitud: int = 20) -> str:
    """Genera una barra de progreso dinámica estilo terminal de carga."""
    if total == 0: return f"`[{'▱' * longitud}] 100%`"
    
    porcentaje = actual / total
    llenos = int(longitud * porcentaje)
    vacios = longitud - llenos
    
    barra = ("▰" * llenos) + ("▱" * vacios)
    porcentaje_entero = int(porcentaje * 100)
    
    return f"`[{barra}] {porcentaje_entero}%`"

# ─────────────────────────────────────────────────────────────
#  1. FORMATO EDITORIAL NATIVO (MODERNO Y LIMPIO)
# ─────────────────────────────────────────────────────────────
def formato_editorial(titulo: str, contenido: str, badge: str = "SYSTEM", pie: str = None) -> str:
    """Genera un mensaje de texto puro con estética de terminal moderna."""
    pie_linea = f"\n\n-# 🛡️ {pie}" if pie else f"\n\n-# 🛡️ {FOOTER_TEXTO}"
    return (
        f"## 💻 {badge} // {titulo.upper()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{contenido}"
        f"{pie_linea}"
    )

# ─────────────────────────────────────────────────────────────
#  2. EMBEDS DE VANGUARDIA (LOGS, TICKETS Y SANCIONES)
# ─────────────────────────────────────────────────────────────
def embed_base(titulo: str, descripcion: str = None, color: int = None) -> discord.Embed:
    """Embed minimalista que se funde con el fondo de Discord."""
    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color or PALETA["primario"],
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=FOOTER_TEXTO, icon_url="https://cdn.discordapp.com/emojis/1183832138484154448.webp")
    return embed

def embed_exito(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"✦ {titulo}", descripcion, PALETA["exito"])

def embed_error(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"⚠️ {titulo}", descripcion, PALETA["error"])

def embed_warn(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"⚠️ {titulo}", descripcion, PALETA["alerta"])

def embed_info(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"ℹ️ {titulo}", descripcion, PALETA["info"])

def embed_lockdown(guild_name: str, razon: str) -> discord.Embed:
    """Visual de emergencia máxima por Raid."""
    embed = discord.Embed(
        title="🚨 ALERTA ROJA: LOCKDOWN INICIADO 🚨",
        description=f"El servidor **{guild_name}** ha entrado en aislamiento preventivo.\n\n**Causa de Activación:**\n> {razon}",
        color=PALETA["peligro"],
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url="https://i.imgur.com/8qGqEBy.gif")
    embed.set_footer(text=f"{FOOTER_TEXTO} • Protocolo Anti-Nuke")
    return embed

def embed_sancion(tipo: str, usuario: discord.Member | discord.User, moderador: discord.Member | discord.User, razon: str, case_id: str, extra: dict = None) -> discord.Embed:
    iconos = {
        "kick": "👢 EXPULSIÓN", "ban": "⛔ EXCLUSIÓN", "tempban": "⏳ SUSPENSIÓN TEMPORAL",
        "softban": "🧹 PURGA", "mute": "🔇 AISLAMIENTO", "warn": "⚠️ ADVERTENCIA",
        "unban": "🔓 EXCLUSIÓN REVOCADA", "jail": "⛓️ ENCARCELAMIENTO",
        "ia_flag": "🧠 MARCAJE HEURÍSTICO"
    }
    titulo = iconos.get(tipo, f"🛡️ ACCIÓN: {tipo.upper()}")
    color = PALETA["error"] if tipo in ["ban", "kick", "softban", "jail"] else (PALETA["oscuro"] if tipo == "ia_flag" else PALETA["alerta"])

    embed = discord.Embed(title=titulo, color=color, timestamp=datetime.now(timezone.utc))
    
    severidad_ia = extra.get("severidad", 0) if extra else 0
    if tipo == "ia_flag" or severidad_ia > 0:
        embed.description = f"**Análisis de Riesgo:**\n{barra_riesgo(severidad_ia)}"

    embed.add_field(name="Sujeto", value=f"{usuario.mention}\n`{usuario.id}`", inline=True)
    embed.add_field(name="Oficial", value=f"{moderador.mention}\n`{moderador.id}`", inline=True)
    embed.add_field(name="Expediente", value=f"`{case_id}`", inline=True)
    embed.add_field(name="Motivo", value=f"> *{razon or 'Sin motivo especificado'}*", inline=False)

    if extra and "severidad" not in extra.keys():
        detalles = " | ".join(f"**{k}:** `{v}`" for k, v in extra.items() if k != "severidad")
        if detalles: embed.add_field(name="Parámetros Extra", value=detalles, inline=False)

    embed.set_footer(text=f"{FOOTER_TEXTO} • Registro Judicial")
    return embed

# ─────────────────────────────────────────────────────────────
#  3. VISTAS INTERACTIVAS (BOTONES Y PAGINACIÓN)
# ─────────────────────────────────────────────────────────────
class ConfirmView(discord.ui.View):
    def __init__(self, autor: discord.Member, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.autor = autor
        self.valor = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("❌ Terminal no autorizada para tu credencial.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Autorizar Protocolo", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.valor = True
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Abortar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.valor = False
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

# ─────────────────────────────────────────────────────────────
#  4. DESPACHO DE AUDITORÍA
# ─────────────────────────────────────────────────────────────
async def enviar_log(bot, guild: discord.Guild, contenido):
    """Canaliza los logs al canal configurado sin interrumpir otros procesos."""
    try:
        config = cargar_config()
        ch_id = config.get("audit_channel") or config.get("log_channel")
        if not ch_id or not guild: return
        canal = guild.get_channel(int(ch_id))
        if not canal: return

        if isinstance(contenido, discord.Embed):
            await canal.send(embed=contenido)
        else:
            await canal.send(str(contenido))
    except Exception:
        pass