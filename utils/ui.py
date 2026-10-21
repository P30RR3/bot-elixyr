"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR SOC // MOTOR VISUAL NEW GEN (LIVE-ACTION & ANSI TERMINAL UI)
  Diseño: Interfaz de Operaciones Tácticas, Bloques ANSI en Vivo, Zero-Lag
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

FOOTER_TEXTO = "Elixyr Sentinel SOC • Advanced Defense Operations"

# Paleta táctica calibrada para modo oscuro puro
PALETA = {
    "primario": 0x1E1F22,   # Discord Dark Surface
    "exito":    0x10B981,   # Emerald Defense
    "error":    0xEF4444,   # Crimson Breach
    "alerta":   0xF59E0B,   # Cyber Amber
    "info":     0x06B6D4,   # Electric Cyan
    "peligro":  0x7F1D1D,   # DEFCON 1 Red
    "ia":       0x8B5CF6    # Cognitive Violet
}

# ─────────────────────────────────────────────────────────────
#  BARRAS DINÁMICAS Y PROTOCOLOS VISUALES
# ─────────────────────────────────────────────────────────────
def barra_progreso(actual: int, total: int, longitud: int = 16) -> str:
    """Genera una barra dinámica de alta visibilidad."""
    if total <= 0:
        return f"`[{'▰' * longitud}] 100%`"
    ratio = min(max(actual / total, 0.0), 1.0)
    llenos = int(longitud * ratio)
    vacios = longitud - llenos
    return f"`[{'▰' * llenos}{'▱' * vacios}] {int(ratio * 100)}%`"

def barra_riesgo(severidad: int) -> str:
    """Barra de amenaza de 0 a 5 niveles de clasificación."""
    cuadros = 5
    llenos = min(max(severidad, 0), cuadros)
    vacios = cuadros - llenos
    porcentaje = int((llenos / cuadros) * 100)
    return f"`[{'█' * llenos}{'░' * vacios}] {porcentaje}% THREAT INDEX`"

def terminal_ansi(lineas: List[str]) -> str:
    """Renderiza líneas de estado con códigos ANSI nativos de Discord."""
    cuerpo = "\n".join(lineas)
    return f"```ansi\n{cuerpo}\n```"

def formato_editorial(titulo: str, contenido: str, badge: str = "SOC", pie: str = None) -> str:
    """Estructura de panel táctico moderno sin saturación de embeds."""
    pie_linea = f"\n\n-# 🛡️ {pie}" if pie else f"\n\n-# 🛡️ {FOOTER_TEXTO}"
    return (
        f"## 💻 [{badge}] // {titulo.upper()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{contenido}"
        f"{pie_linea}"
    )

# ─────────────────────────────────────────────────────────────
#  CONTROLADOR LIVE-ACTION: PROCESO EN TIEMPO REAL
# ─────────────────────────────────────────────────────────────
class LiveActionController:
    """
    Controlador para operaciones que mutan en vivo (escaneos, purgas, asignaciones).
    Actualiza la vista de Discord de forma fluida respetando los rate-limits.
    """
    def __init__(self, ctx_o_interaccion, titulo: str, total_pasos: int = 4):
        self.target = ctx_o_interaccion
        self.titulo = titulo
        self.total_pasos = total_pasos
        self.paso_actual = 0
        self.logs: List[str] = []
        self.mensaje: Optional[discord.Message] = None
        self._last_update = 0.0

    def _render(self, estado: str = "OPERANDO") -> str:
        barra = barra_progreso(self.paso_actual, self.total_pasos)
        ansi_logs = "\n".join(self.logs[-5:]) if self.logs else "[0;37mInicializando entorno...[0m"
        
        return (
            f"### ⚙️ [EN VIVO] // {self.titulo.upper()}\n"
            f"> **Estado:** `{estado}` | **Progreso:** {barra}\n"
            f"```ansi\n{ansi_logs}\n```\n"
            f"-# Elixyr Live Execution Engine"
        )

    async def iniciar(self):
        contenido = self._render()
        if hasattr(self.target, "followup"):
            self.mensaje = await self.target.followup.send(contenido, wait=True)
        else:
            self.mensaje = await self.target.send(contenido)

    async def actualizar(self, texto_log: str, exito: bool = True, avanza: bool = True):
        color_ansi = "[0;32m[+][0m" if exito else "[0;31m[-][0m"
        self.logs.append(f"{color_ansi} {texto_log}")
        if avanza:
            self.paso_actual = min(self.paso_actual + 1, self.total_pasos)

        # Rate-limit safety: no actualizar más rápido de 1.2 segundos
        ahora = asyncio.get_event_loop().time()
        if ahora - self._last_update > 1.2 or self.paso_actual == self.total_pasos:
            self._last_update = ahora
            try:
                if self.mensaje:
                    await self.mensaje.edit(content=self._render())
            except Exception:
                pass

    async def finalizar(self, resumen: str, error: bool = False):
        estado_final = "FALLO TÁCTICO" if error else "COMPLETADO"
        color = "[0;31m[!]" if error else "[0;34m[*]"
        self.logs.append(f"{color} {resumen}[0m")
        self.paso_actual = self.total_pasos
        try:
            if self.mensaje:
                await self.mensaje.edit(content=self._render(estado=estado_final))
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────
#  EMBEDS ESTRUCTURADOS DE ALTA DENSIDAD
# ─────────────────────────────────────────────────────────────
def embed_base(titulo: str, descripcion: str = None, color: int = None) -> discord.Embed:
    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color or PALETA["primario"],
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=FOOTER_TEXTO)
    return embed

def embed_exito(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"✦ {titulo}", descripcion, PALETA["exito"])

def embed_error(titulo: str, descripcion: str = None) -> discord.Embed:
    return embed_base(f"⚠️ {titulo}", descripcion, PALETA["error"])

def embed_sancion(tipo: str, usuario: discord.Member | discord.User, moderador: discord.Member | discord.User, razon: str, case_id: str, extra: dict = None) -> discord.Embed:
    iconos = {
        "ban": "⛔ EXCLUSIÓN DEFINITIVA",
        "kick": "🛑 EXPULSIÓN DE RED",
        "mute": "🔇 AISLAMIENTO PREVENTIVO",
        "warn": "⚠️ ADVERTENCIA DISCIPLINARIA",
        "quarantine": "☣️ CUARENTENA TÁCTICA"
    }
    titulo = iconos.get(tipo.lower(), f"🛡️ ACCIÓN: {tipo.upper()}")
    color = PALETA["error"] if tipo.lower() in ["ban", "kick"] else PALETA["alerta"]

    embed = discord.Embed(title=titulo, color=color, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Sujeto Objetivo", value=f"{usuario.mention}\n`{usuario.id}`", inline=True)
    embed.add_field(name="Oficial Ejecutor", value=f"{moderador.mention}\n`{moderador.id}`", inline=True)
    embed.add_field(name="Expediente", value=f"`{case_id}`", inline=True)
    embed.add_field(name="Fundamento Técnico", value=f"> {razon}", inline=False)

    if extra:
        detalles = " • ".join([f"**{k.capitalize()}:** `{v}`" for k, v in extra.items()])
        embed.add_field(name="Metadatos Forenses", value=detalles, inline=False)

    embed.set_footer(text=f"{FOOTER_TEXTO} • Registro Criptográfico")
    return embed

# ─────────────────────────────────────────────────────────────
#  VISTA DE CONFIRMACIÓN CRÍTICA (TWO-MAN RULE)
# ─────────────────────────────────────────────────────────────
class ConfirmView(discord.ui.View):
    def __init__(self, autor: discord.Member | discord.User, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.autor = autor
        self.valor: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("⛔ Terminal no autorizada para tu huella digital.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Autorizar Operación", style=discord.ButtonStyle.danger, emoji="⚡")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.valor = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Abortar", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.valor = False
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()