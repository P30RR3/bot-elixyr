"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // INTERACTIVE SOC DEFCON TERMINAL (NEW GEN v6.0)
  Capacidades: Dashboard Interactivo en Tiempo Real, Cambio de Postura DEFCON,
               Panic Lockdown de Emergencia y Telemetría Operativa Sincronizada
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ui import formato_editorial

class DefconView(discord.ui.View):
    def __init__(self, bot, guild: discord.Guild):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild = guild

    def _generar_contenido(self) -> str:
        cfg = obtener_guild_config(self.guild.id)
        modo = cfg.get("antiraid_mode", "intermedio").upper()
        automod_st = "🟢 Activo" if cfg.get("automod_enabled", True) else "🔴 Suspendido"
        antiraid_st = "🟢 Activo" if cfg.get("antiraid_enabled", True) else "🔴 Suspendido"
        ia_st = "🟢 Conectado" if cfg.get("automod_ia", True) else "🔴 Inactivo"

        latencia = round(self.bot.latency * 1000)

        return (
            f"> **Infraestructura:** `{self.guild.name}`\n"
            f"> **Postura Táctica Global:** `DEFCON {modo}`\n"
            f"> **Gateway Latency:** `{latencia}ms` | **Motor IA:** {ia_st}\n"
            f"> **Firewall AutoMod:** {automod_st} | **Escudo Anti-Raid:** {antiraid_st}\n\n"
            f"**Matriz de Selección Táctica:**\n"
            f"• 🟢 **DEFCON 5 (Pacífico):** Modo pasivo de observación. Alertas al SOC sin sanciones.\n"
            f"• 🟡 **DEFCON 3 (Intermedio):** Protocolo estándar. Expulsiones automáticas y Shadow Flagging.\n"
            f"• 🔴 **DEFCON 1 (Hardcore):** Tolerancia Cero. Baneos instantáneos a cuentas sospechosas.\n"
            f"• 🚨 **LOCKDOWN:** Cierre hermético de todos los canales públicos."
        )

    async def _actualizar_estado(self, interaction: discord.Interaction, nuevo_modo: str, etiqueta: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** Requiere privilegios de Administrador.", ephemeral=True)

        actualizar_guild_config(self.guild.id, "antiraid_mode", nuevo_modo)
        actualizar_guild_config(self.guild.id, "automod_mode", nuevo_modo)

        panel = formato_editorial(f"TERMINAL DE CONTROL SOC // DEFCON {nuevo_modo.upper()}", self._generar_contenido(), badge="DEFCON-CONSOLE")
        await interaction.response.edit_message(content=panel, view=self)
        await interaction.followup.send(f"🛡️ **Postura Táctica actualizada a DEFCON {nuevo_modo.upper()} ({etiqueta}).**", ephemeral=True)

    @discord.ui.button(label="DEFCON 5 (Pacífico)", style=discord.ButtonStyle.success, emoji="🟢", custom_id="btn_defcon_5")
    async def defcon_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._actualizar_estado(interaction, "pacifico", "Verde")

    @discord.ui.button(label="DEFCON 3 (Intermedio)", style=discord.ButtonStyle.primary, emoji="🟡", custom_id="btn_defcon_3")
    async def defcon_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._actualizar_estado(interaction, "intermedio", "Amarillo")

    @discord.ui.button(label="DEFCON 1 (Hardcore)", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="btn_defcon_1")
    async def defcon_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._actualizar_estado(interaction, "hard", "Rojo")

    @discord.ui.button(label="Pánico (Lockdown)", style=discord.ButtonStyle.secondary, emoji="🚨", custom_id="btn_panic_lockdown")
    async def panic_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ No tienes permisos para activar el protocolo de pánico.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        cerrados = 0
        for canal in self.guild.text_channels:
            ow = canal.overwrites_for(self.guild.default_role)
            if ow.send_messages is not False:
                try:
                    ow.send_messages = False
                    ow.send_messages_in_threads = False
                    await canal.set_permissions(self.guild.default_role, overwrite=ow, reason=f"Panic Lockdown por {interaction.user}")
                    cerrados += 1
                except Exception:
                    pass
        await interaction.followup.send(f"🚨 **PROTOCOLO DE PÁNICO ACTIVADO:** `{cerrados}` canales públicos han sido congelados.", ephemeral=True)

    @discord.ui.button(label="Refrescar Telemetría", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="btn_refresh_soc")
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = formato_editorial(f"TERMINAL DE CONTROL SOC // {self.guild.name.upper()}", self._generar_contenido(), badge="DEFCON-CONSOLE")
        await interaction.response.edit_message(content=panel, view=self)

class SOCPanel(commands.Cog):
    """Módulo de despacho del dashboard interactivo de operaciones de seguridad."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="terminal", aliases=["soc-panel", "dashboard"], description="Despliega la consola interactiva de control táctico DEFCON")
    @commands.has_permissions(administrator=True)
    async def terminal(self, ctx):
        await ctx.defer()
        view = DefconView(self.bot, ctx.guild)
        panel = formato_editorial(f"TERMINAL DE CONTROL SOC // {ctx.guild.name.upper()}", view._generar_contenido(), badge="DEFCON-CONSOLE")
        await ctx.send(panel, view=view)


async def setup(bot):
    await bot.add_cog(SOCPanel(bot))